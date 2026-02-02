"""
Test Question Generation Module
Automatically generates multiple-choice and open-ended questions
"""
from typing import List, Dict, Optional
import json
import random
import ollama
from retrieval import get_retriever

class QuestionGenerator:
    """Generates test questions from course material"""
    
    # Maximum chunk text length to send to LLM
    MAX_CHUNK_LENGTH = 600
    
    # LLM options for faster generation
    LLM_OPTIONS = {
        "temperature": 0.7,
        "num_ctx": 4096,
        "num_predict": 1024,  # Higher for batch generation
    }
    
    # Maximum questions to generate in a single batch
    MAX_BATCH_SIZE = 10
    
    # Required number of options for multiple choice questions
    REQUIRED_OPTIONS = 4
    
    # Characters that indicate garbled/corrupted text (common OCR artifacts)
    GARBLED_CHARS = set('ܐܑܒܓܔܕܖܗܘܙܚܛܜܝܞܟܠܡܢܣܤܥܦܧܨܩܪܫܬ݂݄݆݈݀݁݃݅݇݉݊ݍݎݏ'
                       'ݐݑݒݓݔݕݖݗݘݙݚݛݜݝݞݟݠݡݢݣݤݥݦݧݨݩݪݫݬݭݮݯݰݱݲݳݴݵݶݷݸݹݺݻݼݽݾݿ'
                       '࿀࿁࿂࿃࿄࿅࿆࿇࿈࿉࿊࿋࿌࿎࿏࿐࿑࿒࿓࿔࿕࿖࿗࿘࿙࿚')
    
    def __init__(self, model_name: str = "llama3.1:8b"):
        self.model_name = model_name
        self.retriever = get_retriever()
        # Use retriever's already-loaded chunks
        self._chunks = getattr(self.retriever, 'chunks', None)
        
        # Fallback: load chunks directly if retriever doesn't have them
        if not self._chunks:
            from pathlib import Path
            chunks_path = Path(__file__).parent.parent / "data/processed/chunks.jsonl"
            self._chunks = []
            try:
                with open(chunks_path, "r", encoding="utf-8") as f:
                    for line in f:
                        self._chunks.append(json.loads(line))
                print(f"✓ Question generator loaded {len(self._chunks)} chunks directly")
            except Exception as e:
                print(f"Warning: Could not load chunks: {e}")
                self._chunks = []
    
    def generate_multiple_choice(
        self, 
        section: Optional[str] = None,
        num_questions: int = 5,
        difficulty: str = "medium"
    ) -> List[Dict]:
        """
        Generate multiple-choice questions (batch generation for speed)
        
        Args:
            section: Specific section to generate from (None for random)
            num_questions: Number of questions to generate
            difficulty: "easy", "medium", "hard"
        
        Returns:
            List of multiple-choice questions
        """
        # Limit batch size
        num_questions = min(num_questions, self.MAX_BATCH_SIZE)
        chunks = self._get_random_chunks(section, num_questions)
        
        if not chunks:
            return []
        
        # Try batch generation first (faster)
        try:
            questions = self._generate_mcq_batch(chunks, difficulty)
            if questions:
                return questions
        except Exception as e:
            print(f"Batch generation failed, falling back to sequential: {e}")
        
        # Fallback to sequential generation
        questions = []
        for chunk in chunks:
            try:
                question = self._generate_mcq_from_chunk(chunk, difficulty)
                if question:
                    questions.append(question)
            except Exception as e:
                print(f"Error generating question: {e}")
                continue
        
        return questions
    
    def generate_open_ended(
        self,
        section: Optional[str] = None,
        num_questions: int = 5,
        difficulty: str = "medium"
    ) -> List[Dict]:
        """
        Generate open-ended questions (batch generation for speed)
        
        Args:
            section: Specific section
            num_questions: Number of questions
            difficulty: "easy", "medium", "hard"
        """
        # Limit batch size
        num_questions = min(num_questions, self.MAX_BATCH_SIZE)
        chunks = self._get_random_chunks(section, num_questions)
        
        if not chunks:
            return []
        
        # Try batch generation first (faster)
        try:
            questions = self._generate_open_batch(chunks, difficulty)
            if questions:
                return questions
        except Exception as e:
            print(f"Batch generation failed, falling back to sequential: {e}")
        
        # Fallback to sequential generation
        questions = []
        for chunk in chunks:
            try:
                question = self._generate_open_question_from_chunk(chunk, difficulty)
                if question:
                    questions.append(question)
            except Exception as e:
                print(f"Error generating question: {e}")
                continue
        
        return questions
    
    def _has_garbled_text(self, text: str) -> bool:
        """Check if text contains garbled/corrupted characters"""
        garbled_count = sum(1 for char in text if char in self.GARBLED_CHARS)
        # If more than 1% of characters are garbled, consider it bad
        return garbled_count > len(text) * 0.01
    
    def _clean_text(self, text: str) -> str:
        """Remove or replace garbled characters from text"""
        # Remove garbled characters
        cleaned = ''.join(char for char in text if char not in self.GARBLED_CHARS)
        # Also remove common OCR artifacts and normalize whitespace
        cleaned = ' '.join(cleaned.split())
        return cleaned
    
    def _get_random_chunks(
        self,
        section: Optional[str],
        num: int
    ) -> List[Dict]:
        """Get random chunks from the material (uses cached chunks)"""
        # Filter chunks
        filtered_chunks = []
        for chunk in self._chunks:
            # Filter by section if specified
            if section is None or section.lower() in chunk["section_title"].lower():
                # Check minimum length
                if len(chunk["text"]) > 200:
                    # Skip chunks with garbled text
                    if not self._has_garbled_text(chunk["text"]):
                        filtered_chunks.append(chunk)
        
        if len(filtered_chunks) > num:
            return random.sample(filtered_chunks, num)
        return filtered_chunks
    
    def _truncate_chunk_text(self, text: str) -> str:
        """Truncate chunk text to maximum length"""
        # Clean the text first
        text = self._clean_text(text)
        if len(text) <= self.MAX_CHUNK_LENGTH:
            return text
        return text[:self.MAX_CHUNK_LENGTH] + "..."
    
    def _validate_mcq(self, question: Dict) -> bool:
        """Validate a multiple choice question"""
        # Must have question text
        if not question.get("question") or len(question["question"]) < 10:
            return False
        
        # Must have exactly 4 options
        options = question.get("options", [])
        if len(options) != self.REQUIRED_OPTIONS:
            return False
        
        # Options must not be empty or garbled
        for opt in options:
            if not opt or len(opt) < 1:
                return False
            if self._has_garbled_text(str(opt)):
                return False
        
        # Question text must not be garbled
        if self._has_garbled_text(question["question"]):
            return False
        
        # correct_answer must be valid index
        correct = question.get("correct_answer")
        if correct is None or not isinstance(correct, int) or correct < 0 or correct >= len(options):
            return False
        
        return True
    
    def _validate_open_question(self, question: Dict) -> bool:
        """Validate an open-ended question"""
        # Must have question text
        if not question.get("question") or len(question["question"]) < 10:
            return False
        
        # Question text must not be garbled
        if self._has_garbled_text(question["question"]):
            return False
        
        # Must have key_points
        key_points = question.get("key_points", [])
        if not key_points or len(key_points) < 1:
            return False
        
        return True
    
    def _parse_json_response(self, content: str) -> List[Dict]:
        """Parse JSON from LLM response with robust error handling"""
        if not content:
            raise ValueError("Empty response from LLM")
        
        original_content = content
        content = content.strip()
        
        # Try to extract JSON from code blocks
        if "```json" in content:
            try:
                content = content.split("```json")[1].split("```")[0].strip()
            except IndexError:
                pass
        elif "```" in content:
            parts = content.split("```")
            if len(parts) >= 2:
                content = parts[1].strip()
        
        # Try to find JSON array in the content
        # Look for [ ... ] pattern
        start_idx = content.find('[')
        end_idx = content.rfind(']')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            content = content[start_idx:end_idx + 1]
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Content was: {content[:500]}...")
            raise
    
    def _generate_mcq_batch(self, chunks: List[Dict], difficulty: str) -> List[Dict]:
        """Generate multiple MCQs in a single LLM call (batch generation)"""
        
        difficulty_instructions = {
            "easy": "Въпросите трябва да изискват прости дефиниции или факти.",
            "medium": "Въпросите трябва да изискват разбиране на концепциите.",
            "hard": "Въпросите трябва да изискват задълбочено разбиране и приложение."
        }
        
        # Build combined context from all chunks
        contexts = []
        for i, chunk in enumerate(chunks, 1):
            text = self._truncate_chunk_text(chunk['text'])
            contexts.append(f"[Текст {i} - Страница {chunk['page']}]\n{text}")
        
        combined_context = "\n\n".join(contexts)
        num_questions = len(chunks)
        
        prompt = f"""Генерирай {num_questions} multiple-choice въпроса базирани на следните текстове от учебен материал по Information Retrieval.

{combined_context}

Ниво на трудност: {difficulty}
{difficulty_instructions.get(difficulty, '')}

Върни JSON масив с {num_questions} въпроса във формат:
[
  {{
    "question": "Въпрос на български език",
    "options": ["Отговор А", "Отговор Б", "Отговор В", "Отговор Г"],
    "correct_answer": 0,
    "explanation": "Обяснение защо това е верният отговор",
    "source_index": 1
  }}
]

ВАЖНИ ПРАВИЛА:
- Генерирай точно {num_questions} въпроса
- ВСЕКИ въпрос ТРЯБВА да има ТОЧНО 4 опции (не 2, не 3, а точно 4!)
- correct_answer е индекс 0-3
- source_index показва от кой текст е въпросът (1-{num_questions})
- Използвай САМО български език и ЧЕТИМ текст
- НЕ използвай специални символи или формули - опиши ги с думи
- Върни САМО валиден JSON масив

JSON:"""

        response = ollama.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            options=self.LLM_OPTIONS
        )
        
        content = response['message']['content']
        questions_data = self._parse_json_response(content)
        
        # Ensure it's a list
        if not isinstance(questions_data, list):
            questions_data = [questions_data]
        
        # Add metadata from chunks and validate
        result = []
        for q in questions_data:
            if not isinstance(q, dict) or "question" not in q:
                continue
            
            source_idx = q.get("source_index", 1) - 1
            if 0 <= source_idx < len(chunks):
                chunk = chunks[source_idx]
            else:
                chunk = chunks[0]
            
            q["type"] = "multiple_choice"
            q["difficulty"] = difficulty
            q["page"] = chunk["page"]
            q["section"] = chunk["section_title"]
            q["chunk_id"] = chunk["chunk_id"]
            q.pop("source_index", None)
            
            # Validate the question - must have exactly 4 options and no garbled text
            if self._validate_mcq(q):
                result.append(q)
            else:
                print(f"Skipping invalid MCQ: {q.get('question', 'NO QUESTION')[:50]}...")
        
        return result
    
    def _generate_open_batch(self, chunks: List[Dict], difficulty: str) -> List[Dict]:
        """Generate multiple open-ended questions in a single LLM call"""
        
        difficulty_instructions = {
            "easy": "Въпросите трябва да изискват кратки дефиниции (2-3 изречения).",
            "medium": "Въпросите трябва да изискват по-подробни обяснения с примери.",
            "hard": "Въпросите трябва да изискват задълбочен анализ и сравнения."
        }
        
        # Build combined context from all chunks
        contexts = []
        for i, chunk in enumerate(chunks, 1):
            text = self._truncate_chunk_text(chunk['text'])
            contexts.append(f"[Текст {i} - Страница {chunk['page']}]\n{text}")
        
        combined_context = "\n\n".join(contexts)
        num_questions = len(chunks)
        
        prompt = f"""Генерирай {num_questions} отворени въпроса базирани на следните текстове от учебен материал по Information Retrieval.

{combined_context}

Ниво на трудност: {difficulty}
{difficulty_instructions.get(difficulty, '')}

Върни JSON масив с {num_questions} въпроса във формат:
[
  {{
    "question": "Въпрос 1",
    "key_points": ["Точка 1", "Точка 2", "Точка 3"],
    "sample_answer": "Примерен кратък отговор",
    "source_index": 1
  }}
]

ПРАВИЛА:
- Генерирай точно {num_questions} въпроса
- Всеки въпрос има 3-5 ключови точки
- source_index показва от кой текст е въпросът (1-{num_questions})
- Използвай български език
- Върни САМО валиден JSON масив, без допълнителен текст

JSON:"""

        response = ollama.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            options=self.LLM_OPTIONS
        )
        
        content = response['message']['content']
        questions_data = self._parse_json_response(content)
        
        # Ensure it's a list
        if not isinstance(questions_data, list):
            questions_data = [questions_data]
        
        # Add metadata from chunks and validate
        result = []
        for q in questions_data:
            if not isinstance(q, dict) or "question" not in q:
                continue
                
            source_idx = q.get("source_index", 1) - 1
            if 0 <= source_idx < len(chunks):
                chunk = chunks[source_idx]
            else:
                chunk = chunks[0]
            
            q["type"] = "open_ended"
            q["difficulty"] = difficulty
            q["page"] = chunk["page"]
            q["section"] = chunk["section_title"]
            q["chunk_id"] = chunk["chunk_id"]
            q.pop("source_index", None)
            
            # Validate the question
            if self._validate_open_question(q):
                result.append(q)
            else:
                print(f"Skipping invalid open question: {q.get('question', 'NO QUESTION')[:50]}...")
        
        return result
    
    def _generate_mcq_from_chunk(self, chunk: Dict, difficulty: str = "medium") -> Optional[Dict]:
        """Generate a multiple-choice question from a chunk (fallback sequential method)"""
        
        difficulty_instructions = {
            "easy": "Въпросът трябва да изисква проста дефиниция или факт директно от текста.",
            "medium": "Въпросът трябва да изисква разбиране на концепцията.",
            "hard": "Въпросът трябва да изисква задълбочено разбиране и приложение."
        }
        
        # Truncate chunk text
        text = self._truncate_chunk_text(chunk['text'])
        
        prompt = f"""Базирайки се на следния текст, генерирай един multiple-choice въпрос.

Текст:
{text}

Ниво: {difficulty}. {difficulty_instructions.get(difficulty, '')}

JSON формат:
{{"question": "Въпрос на български", "options": ["Отговор А", "Отговор Б", "Отговор В", "Отговор Г"], "correct_answer": 0, "explanation": "Обяснение"}}

ВАЖНО: Трябва да има ТОЧНО 4 опции! Използвай само четим български текст, без специални символи.

Върни САМО JSON:"""

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                options=self.LLM_OPTIONS
            )

            content = response['message']['content'].strip()

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            question_data = json.loads(content)
            
            question_data["type"] = "multiple_choice"
            question_data["difficulty"] = difficulty
            question_data["page"] = chunk["page"]
            question_data["section"] = chunk["section_title"]
            question_data["chunk_id"] = chunk["chunk_id"]
            
            # Validate the question
            if self._validate_mcq(question_data):
                return question_data
            else:
                print(f"Invalid MCQ generated, skipping")
                return None
            
        except Exception as e:
            print(f"Error parsing MCQ: {e}")
            return None
    
    def _generate_open_question_from_chunk(
        self, 
        chunk: Dict, 
        difficulty: str
    ) -> Optional[Dict]:
        """Generate an open-ended question from a chunk (fallback sequential method)"""
        
        difficulty_instructions = {
            "easy": "Въпросът трябва да изисква кратка дефиниция (2-3 изречения).",
            "medium": "Въпросът трябва да изисква по-подробно обяснение с примери.",
            "hard": "Въпросът трябва да изисква задълбочен анализ и сравнение."
        }
        
        # Truncate chunk text
        text = self._truncate_chunk_text(chunk['text'])
        
        prompt = f"""Базирайки се на следния текст, генерирай един отворен въпрос.

Текст:
{text}

Ниво: {difficulty}. {difficulty_instructions.get(difficulty, '')}

JSON формат:
{{"question": "...", "key_points": ["1", "2", "3"], "sample_answer": "..."}}

Върни САМО JSON:"""

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                options=self.LLM_OPTIONS
            )
            
            content = response['message']['content'].strip()

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            question_data = json.loads(content)

            question_data["type"] = "open_ended"
            question_data["difficulty"] = difficulty
            question_data["page"] = chunk["page"]
            question_data["section"] = chunk["section_title"]
            question_data["chunk_id"] = chunk["chunk_id"]
            
            # Validate the question
            if self._validate_open_question(question_data):
                return question_data
            else:
                print(f"Invalid open question generated, skipping")
                return None
            
        except Exception as e:
            print(f"Error parsing open question: {e}")
            return None


def get_question_generator(model_name: str = "llama3.1:8b") -> QuestionGenerator:
    """Get a question generator instance"""
    return QuestionGenerator(model_name=model_name)