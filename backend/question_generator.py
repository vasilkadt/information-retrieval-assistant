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
    
    def __init__(self, model_name: str = "llama3.1:8b"):
        self.model_name = model_name
        self.retriever = get_retriever()
    
    def generate_multiple_choice(
        self, 
        section: Optional[str] = None,
        num_questions: int = 5,
        difficulty: str = "medium"
    ) -> List[Dict]:
        """
        Generate multiple-choice questions
        
        Args:
            section: Specific section to generate from (None for random)
            num_questions: Number of questions to generate
            difficulty: "easy", "medium", "hard"
        
        Returns:
            List of multiple-choice questions
        """
        questions = []
        
        chunks = self._get_random_chunks(section, num_questions)
        
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
        Generate open-ended questions
        
        Args:
            section: Specific section
            num_questions: Number of questions
            difficulty: "easy", "medium", "hard"
        """
        questions = []
        chunks = self._get_random_chunks(section, num_questions)
        
        for chunk in chunks:
            try:
                question = self._generate_open_question_from_chunk(chunk, difficulty)
                if question:
                    questions.append(question)
            except Exception as e:
                print(f"Error generating question: {e}")
                continue
        
        return questions
    
    def _get_random_chunks(
        self,
        section: Optional[str],
        num: int
    ) -> List[Dict]:
        """Get random chunks from the material"""
        from pathlib import Path
        chunks_path = Path(__file__).parent.parent / "data/processed/chunks.jsonl"
        
        all_chunks = []
        with open(chunks_path, "r", encoding="utf-8") as f:
            for line in f:
                chunk = json.loads(line)
                # Filter by section if specified
                if section is None or section.lower() in chunk["section_title"].lower():
                    if len(chunk["text"]) > 200:
                        all_chunks.append(chunk)
        
        if len(all_chunks) > num:
            return random.sample(all_chunks, num)
        return all_chunks
    
    def _generate_mcq_from_chunk(self, chunk: Dict, difficulty: str = "medium") -> Optional[Dict]:
        """Generate a multiple-choice question from a chunk"""
        
        difficulty_instructions = {
            "easy": "Въпросът трябва да изисква проста дефиниция или факт директно от текста. Неверните отговори трябва да са очевидно грешни.",
            "medium": "Въпросът трябва да изисква разбиране на концепцията. Неверните отговори трябва да са правдоподобни, но погрешни.",
            "hard": "Въпросът трябва да изисква задълбочено разбиране, приложение или сравнение. Неверните отговори трябва да са много близки до верния, но имат фини разлики."
        }
        
        prompt = f"""Базирайки се на следния текст от учебен материал по Information Retrieval, генерирай един multiple-choice въпрос.

Текст:
{chunk['text']}

Ниво на трудност: {difficulty}
{difficulty_instructions.get(difficulty, '')}

Създай въпрос със следния JSON формат:
{{
  "question": "Въпросът тук",
  "options": [
    "Отговор А",
    "Отговор Б",
    "Отговор В",
    "Отговор Г"
  ],
  "correct_answer": 0,
  "explanation": "Кратко обяснение защо верният отговор е правилен"
}}

ПРАВИЛА:
- Въпросът трябва да е точен и базиран на текста
- Дай 4 опции (индекси 0, 1, 2, 3)
- Само един отговор е верен
- Използвай български език
- Върни САМО JSON, без допълнителен текст

JSON:"""

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.7}
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
            
            return question_data
            
        except Exception as e:
            print(f"Error parsing MCQ: {e}")
            return None
    
    def _generate_open_question_from_chunk(
        self, 
        chunk: Dict, 
        difficulty: str
    ) -> Optional[Dict]:
        """Generate an open-ended question from a chunk"""
        
        difficulty_instructions = {
            "easy": "Въпросът трябва да изисква кратка дефиниция или обяснение (2-3 изречения).",
            "medium": "Въпросът трябва да изисква по-подробно обяснение с примери (параграф).",
            "hard": "Въпросът трябва да изисква задълбочен анализ, сравнение или приложение на концепции (няколко параграфа)."
        }
        
        prompt = f"""Базирайки се на следния текст от учебен материал по Information Retrieval, генерирай един отворен въпрос за есе/размисъл.

Текст:
{chunk['text']}

Ниво на трудност: {difficulty}
{difficulty_instructions.get(difficulty, '')}

Създай въпрос със следния JSON формат:
{{
  "question": "Въпросът тук",
  "key_points": [
    "Ключова точка 1, която трябва да се включи в отговора",
    "Ключова точка 2",
    "Ключова точка 3"
  ],
  "sample_answer": "Примерен отговор (2-3 изречения)"
}}

ПРАВИЛА:
- Въпросът трябва да насърчава критично мислене
- Включи 3-5 ключови точки за оценка
- Примерният отговор трябва да е кратък образец
- Използвай български език
- Върни САМО JSON, без допълнителен текст

JSON:"""

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.7}
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
            
            return question_data
            
        except Exception as e:
            print(f"Error parsing open question: {e}")
            return None


def get_question_generator(model_name: str = "llama3.1:8b") -> QuestionGenerator:
    """Get a question generator instance"""
    return QuestionGenerator(model_name=model_name)