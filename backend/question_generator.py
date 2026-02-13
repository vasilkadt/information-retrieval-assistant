"""
Test Question Generation Module
Generates multiple-choice and open-ended questions with caching for speed.
Strategy: Cache-first → serve from DB instantly, generate only when needed.
"""
from typing import List, Dict, Optional
import json
import random
import hashlib
import asyncio
from concurrent.futures import ThreadPoolExecutor
import ollama
from retrieval import get_retriever
from database import get_db

# Thread pool for parallel LLM calls
_executor = ThreadPoolExecutor(max_workers=3)


class QuestionGenerator:
    """Generates test questions from course material with caching"""
    
    MAX_CHUNK_LENGTH = 600
    MAX_BATCH_SIZE = 10
    REQUIRED_OPTIONS = 4
    
    # Optimized LLM options for faster generation
    LLM_OPTIONS = {
        "temperature": 0.7,
        "num_ctx": 2048,      # Reduced context window (faster)
        "num_predict": 512,   # Reduced for single questions
    }
    
    LLM_OPTIONS_BATCH = {
        "temperature": 0.7,
        "num_ctx": 4096,
        "num_predict": 1024,
    }
    
    # Characters that indicate garbled/corrupted text
    GARBLED_CHARS = set('ܐܑܒܓܔܕܖܗܘܙܚܛܜܝܞܟܠܡܢܣܤܥܦܧܨܩܪܫܬ݂݄݆݈݀݁݃݅݇݉݊ݍݎݏ'
                       'ݐݑݒݓݔݕݖݗݘݙݚݛݜݝݞݟݠݡݢݣݤݥݦݧݨݩݪݫݬݭݮݯݰݱݲݳݴݵݶݷݸݹݺݻݼݽݾݿ'
                       '࿀࿁࿂࿃࿄࿅࿆࿇࿈࿉࿊࿋࿌࿎࿏࿐࿑࿒࿓࿔࿕࿖࿗࿘࿙࿚')
    
    def __init__(self, model_name: str = "llama3.1:8b"):
        self.model_name = model_name
        self.retriever = get_retriever()
        self.db = get_db()
        self._chunks = getattr(self.retriever, 'chunks', None)
        
        if not self._chunks:
            from pathlib import Path
            chunks_path = Path(__file__).parent.parent / "data/processed/chunks.jsonl"
            self._chunks = []
            try:
                with open(chunks_path, "r", encoding="utf-8") as f:
                    for line in f:
                        self._chunks.append(json.loads(line))
            except Exception as e:
                print(f"Warning: Could not load chunks: {e}")
    
    # ── Cache helpers ──────────────────────────────────────────────────
    
    def _cache_key(self, chunk_id: str, question_type: str, difficulty: str) -> str:
        """Generate a unique cache key for a chunk+type+difficulty combination"""
        raw = f"{chunk_id}:{question_type}:{difficulty}"
        return hashlib.md5(raw.encode()).hexdigest()
    
    def _get_cached(self, question_type: str, difficulty: str, num: int) -> List[Dict]:
        """Get cached questions from database"""
        return self.db.get_cached_questions(question_type, difficulty, num)
    
    def _save_to_cache(self, question: Dict) -> None:
        """Save a generated question to cache"""
        cache_key = self._cache_key(
            question.get("chunk_id", ""),
            question.get("type", ""),
            question.get("difficulty", "")
        )
        try:
            self.db.cache_question(
                cache_key=cache_key,
                question_type=question.get("type", ""),
                difficulty=question.get("difficulty", ""),
                chunk_id=question.get("chunk_id", ""),
                question_data=question
            )
        except Exception:
            pass  # Cache write failures are non-critical
    
    # ── Public API ─────────────────────────────────────────────────────
    
    def generate_multiple_choice(
        self, 
        section: Optional[str] = None,
        num_questions: int = 5,
        difficulty: str = "medium"
    ) -> List[Dict]:
        """
        Generate multiple-choice questions with cache-first strategy.
        1. Check cache for existing questions
        2. If enough cached → serve instantly
        3. If not enough → generate only the missing ones
        """
        num_questions = min(num_questions, self.MAX_BATCH_SIZE)
        
        # Step 1: Try cache first
        cached = self._get_cached("multiple_choice", difficulty, num_questions)
        if len(cached) >= num_questions:
            return random.sample(cached, num_questions)
        
        # Step 2: Need to generate more
        num_to_generate = num_questions - len(cached)
        chunks = self._get_random_chunks(section, num_to_generate)
        
        if not chunks and not cached:
            return []
        
        # Step 3: Generate new questions
        generated = []
        if chunks:
            try:
                generated = self._generate_mcq_batch(chunks, difficulty)
            except Exception:
                # Fallback to sequential
                for chunk in chunks:
                    try:
                        q = self._generate_mcq_from_chunk(chunk, difficulty)
                        if q:
                            generated.append(q)
                    except Exception:
                        continue
        
        # Step 4: Cache newly generated questions
        for q in generated:
            self._save_to_cache(q)
        
        # Step 5: Combine cached + generated
        all_questions = cached + generated
        if len(all_questions) > num_questions:
            return random.sample(all_questions, num_questions)
        return all_questions
    
    def generate_open_ended(
        self,
        section: Optional[str] = None,
        num_questions: int = 5,
        difficulty: str = "medium"
    ) -> List[Dict]:
        """
        Generate open-ended questions with cache-first strategy.
        Same flow as multiple_choice.
        """
        num_questions = min(num_questions, self.MAX_BATCH_SIZE)
        
        # Step 1: Try cache first
        cached = self._get_cached("open_ended", difficulty, num_questions)
        if len(cached) >= num_questions:
            return random.sample(cached, num_questions)
        
        # Step 2: Need to generate more
        num_to_generate = num_questions - len(cached)
        chunks = self._get_random_chunks(section, num_to_generate)
        
        if not chunks and not cached:
            return []
        
        # Step 3: Generate new questions
        generated = []
        if chunks:
            try:
                generated = self._generate_open_batch(chunks, difficulty)
            except Exception:
                for chunk in chunks:
                    try:
                        q = self._generate_open_question_from_chunk(chunk, difficulty)
                        if q:
                            generated.append(q)
                    except Exception:
                        continue
        
        # Step 4: Cache newly generated questions
        for q in generated:
            self._save_to_cache(q)
        
        # Step 5: Combine cached + generated
        all_questions = cached + generated
        if len(all_questions) > num_questions:
            return random.sample(all_questions, num_questions)
        return all_questions
    
    async def generate_multiple_choice_async(
        self,
        section: Optional[str] = None,
        num_questions: int = 5,
        difficulty: str = "medium"
    ) -> List[Dict]:
        """Async version: parallel LLM calls for faster generation"""
        num_questions = min(num_questions, self.MAX_BATCH_SIZE)
        
        # Try cache first
        cached = self._get_cached("multiple_choice", difficulty, num_questions)
        if len(cached) >= num_questions:
            return random.sample(cached, num_questions)
        
        num_to_generate = num_questions - len(cached)
        chunks = self._get_random_chunks(section, num_to_generate)
        
        if not chunks and not cached:
            return []
        
        # Generate concurrently using thread pool
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(_executor, self._generate_mcq_from_chunk, chunk, difficulty)
            for chunk in chunks
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        generated = [r for r in results if isinstance(r, dict)]
        
        for q in generated:
            self._save_to_cache(q)
        
        all_questions = cached + generated
        if len(all_questions) > num_questions:
            return random.sample(all_questions, num_questions)
        return all_questions
    
    async def generate_open_ended_async(
        self,
        section: Optional[str] = None,
        num_questions: int = 5,
        difficulty: str = "medium"
    ) -> List[Dict]:
        """Async version: parallel LLM calls for faster generation"""
        num_questions = min(num_questions, self.MAX_BATCH_SIZE)
        
        cached = self._get_cached("open_ended", difficulty, num_questions)
        if len(cached) >= num_questions:
            return random.sample(cached, num_questions)
        
        num_to_generate = num_questions - len(cached)
        chunks = self._get_random_chunks(section, num_to_generate)
        
        if not chunks and not cached:
            return []
        
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(_executor, self._generate_open_question_from_chunk, chunk, difficulty)
            for chunk in chunks
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        generated = [r for r in results if isinstance(r, dict)]
        
        for q in generated:
            self._save_to_cache(q)
        
        all_questions = cached + generated
        if len(all_questions) > num_questions:
            return random.sample(all_questions, num_questions)
        return all_questions
    
    # ── Text helpers ───────────────────────────────────────────────────
    
    def _has_garbled_text(self, text: str) -> bool:
        """Check if text contains garbled/corrupted characters"""
        garbled_count = sum(1 for char in text if char in self.GARBLED_CHARS)
        return garbled_count > len(text) * 0.01
    
    def _clean_text(self, text: str) -> str:
        """Remove garbled characters from text"""
        cleaned = ''.join(char for char in text if char not in self.GARBLED_CHARS)
        return ' '.join(cleaned.split())
    
    def _get_random_chunks(self, section: Optional[str], num: int) -> List[Dict]:
        """Get random clean chunks from the material"""
        filtered = [
            chunk for chunk in self._chunks
            if (section is None or section.lower() in chunk["section_title"].lower())
            and len(chunk["text"]) > 200
            and not self._has_garbled_text(chunk["text"])
        ]
        if len(filtered) > num:
            return random.sample(filtered, num)
        return filtered
    
    def _truncate_chunk_text(self, text: str) -> str:
        """Truncate and clean chunk text"""
        text = self._clean_text(text)
        if len(text) <= self.MAX_CHUNK_LENGTH:
            return text
        return text[:self.MAX_CHUNK_LENGTH] + "..."
    
    # ── Validation ─────────────────────────────────────────────────────
    
    def _validate_mcq(self, question: Dict) -> bool:
        """Validate a multiple choice question"""
        if not question.get("question") or len(question["question"]) < 10:
            return False
        options = question.get("options", [])
        if len(options) != self.REQUIRED_OPTIONS:
            return False
        for opt in options:
            if not opt or len(opt) < 1 or self._has_garbled_text(str(opt)):
                return False
        if self._has_garbled_text(question["question"]):
            return False
        correct = question.get("correct_answer")
        if correct is None or not isinstance(correct, int) or correct < 0 or correct >= len(options):
            return False
        return True
    
    def _validate_open_question(self, question: Dict) -> bool:
        """Validate an open-ended question"""
        if not question.get("question") or len(question["question"]) < 10:
            return False
        if self._has_garbled_text(question["question"]):
            return False
        if not question.get("key_points") or len(question["key_points"]) < 1:
            return False
        return True
    
    # ── JSON parsing ───────────────────────────────────────────────────
    
    def _parse_json_response(self, content: str) -> List[Dict]:
        """Parse JSON from LLM response"""
        if not content:
            raise ValueError("Empty response from LLM")
        
        content = content.strip()
        
        if "```json" in content:
            try:
                content = content.split("```json")[1].split("```")[0].strip()
            except IndexError:
                pass
        elif "```" in content:
            parts = content.split("```")
            if len(parts) >= 2:
                content = parts[1].strip()
        
        start_idx = content.find('[')
        end_idx = content.rfind(']')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            content = content[start_idx:end_idx + 1]
        
        return json.loads(content)
    
    # ── Batch generation (single LLM call for multiple questions) ──────
    
    def _generate_mcq_batch(self, chunks: List[Dict], difficulty: str) -> List[Dict]:
        """Generate multiple MCQs in a single LLM call"""
        
        difficulty_map = {
            "easy": "прости дефиниции",
            "medium": "разбиране на концепции",
            "hard": "задълбочен анализ"
        }
        
        contexts = []
        for i, chunk in enumerate(chunks, 1):
            text = self._truncate_chunk_text(chunk['text'])
            contexts.append(f"[Текст {i}]\n{text}")
        
        n = len(chunks)
        prompt = f"""Генерирай {n} multiple-choice въпроса ({difficulty_map.get(difficulty, '')}).

{"---".join(contexts)}

JSON масив с {n} въпроса:
[{{"question":"...","options":["А","Б","В","Г"],"correct_answer":0,"explanation":"...","source_index":1}}]

ПРАВИЛА: точно {n} въпроса, точно 4 опции, correct_answer 0-3, source_index 1-{n}, български, без формули. САМО JSON:"""

        response = ollama.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            options=self.LLM_OPTIONS_BATCH
        )
        
        questions_data = self._parse_json_response(response['message']['content'])
        if not isinstance(questions_data, list):
            questions_data = [questions_data]
        
        result = []
        for q in questions_data:
            if not isinstance(q, dict) or "question" not in q:
                continue
            
            source_idx = q.get("source_index", 1) - 1
            chunk = chunks[source_idx] if 0 <= source_idx < len(chunks) else chunks[0]
            
            q["type"] = "multiple_choice"
            q["difficulty"] = difficulty
            q["page"] = chunk["page"]
            q["section"] = chunk["section_title"]
            q["chunk_id"] = chunk["chunk_id"]
            q.pop("source_index", None)
            
            if self._validate_mcq(q):
                result.append(q)
        
        return result
    
    def _generate_open_batch(self, chunks: List[Dict], difficulty: str) -> List[Dict]:
        """Generate multiple open-ended questions in a single LLM call"""
        
        difficulty_map = {
            "easy": "кратки дефиниции (2-3 изречения)",
            "medium": "обяснения с примери",
            "hard": "задълбочен анализ и сравнения"
        }
        
        contexts = []
        for i, chunk in enumerate(chunks, 1):
            text = self._truncate_chunk_text(chunk['text'])
            contexts.append(f"[Текст {i}]\n{text}")
        
        n = len(chunks)
        prompt = f"""Генерирай {n} отворени въпроса ({difficulty_map.get(difficulty, '')}).

{"---".join(contexts)}

JSON масив:
[{{"question":"...","key_points":["1","2","3"],"sample_answer":"...","source_index":1}}]

ПРАВИЛА: {n} въпроса, 3-5 ключови точки, source_index 1-{n}, български. САМО JSON:"""

        response = ollama.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            options=self.LLM_OPTIONS_BATCH
        )
        
        questions_data = self._parse_json_response(response['message']['content'])
        if not isinstance(questions_data, list):
            questions_data = [questions_data]
        
        result = []
        for q in questions_data:
            if not isinstance(q, dict) or "question" not in q:
                continue
                
            source_idx = q.get("source_index", 1) - 1
            chunk = chunks[source_idx] if 0 <= source_idx < len(chunks) else chunks[0]
            
            q["type"] = "open_ended"
            q["difficulty"] = difficulty
            q["page"] = chunk["page"]
            q["section"] = chunk["section_title"]
            q["chunk_id"] = chunk["chunk_id"]
            q.pop("source_index", None)
            
            if self._validate_open_question(q):
                result.append(q)
        
        return result
    
    # ── Sequential fallback (one question per LLM call) ────────────────
    
    def _generate_mcq_from_chunk(self, chunk: Dict, difficulty: str = "medium") -> Optional[Dict]:
        """Generate a single MCQ from a chunk"""
        text = self._truncate_chunk_text(chunk['text'])
        
        prompt = f"""Генерирай 1 multiple-choice въпрос от текста.

{text}

Ниво: {difficulty}. JSON: {{"question":"...","options":["А","Б","В","Г"],"correct_answer":0,"explanation":"..."}}
ТОЧНО 4 опции, български, без формули. САМО JSON:"""

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
            
            q = json.loads(content)
            q["type"] = "multiple_choice"
            q["difficulty"] = difficulty
            q["page"] = chunk["page"]
            q["section"] = chunk["section_title"]
            q["chunk_id"] = chunk["chunk_id"]
            
            return q if self._validate_mcq(q) else None
        except Exception:
            return None
    
    def _generate_open_question_from_chunk(self, chunk: Dict, difficulty: str = "medium") -> Optional[Dict]:
        """Generate a single open-ended question from a chunk"""
        text = self._truncate_chunk_text(chunk['text'])
        
        prompt = f"""Генерирай 1 отворен въпрос от текста.

{text}

Ниво: {difficulty}. JSON: {{"question":"...","key_points":["1","2","3"],"sample_answer":"..."}}
Български. САМО JSON:"""

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
            
            q = json.loads(content)
            q["type"] = "open_ended"
            q["difficulty"] = difficulty
            q["page"] = chunk["page"]
            q["section"] = chunk["section_title"]
            q["chunk_id"] = chunk["chunk_id"]
            
            return q if self._validate_open_question(q) else None
        except Exception:
            return None


def get_question_generator(model_name: str = "llama3.1:8b") -> QuestionGenerator:
    """Get a question generator instance"""
    return QuestionGenerator(model_name=model_name)
