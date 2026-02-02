"""
RAG (Retrieval-Augmented Generation) Pipeline
Combines retrieval with Ollama/Llama for answer generation
"""
from typing import List, Dict, Optional
import re
import ollama
from retrieval import get_retriever

class RAGPipeline:
    """
    RAG (Retrieval-Augmented Generation) Pipeline for Question Answering
    
    Combines hybrid retrieval (BM25 + vector search) with Llama LLM to answer
    student questions about Information Retrieval based on lecture notes.
    
    Architecture:
        1. Retrieve relevant chunks from lecture notes (hybrid search)
        2. Build context from retrieved chunks with source attribution
        3. Generate prompt with system instructions and context
        4. Query Llama model via Ollama for answer generation
        5. Return a structured response with answer and sources
    """
    
    # Minimum relevance score threshold for including chunks
    MIN_RELEVANCE_SCORE = 0.35
    
    # Maximum number of chunks to include in context (reduces LLM processing time)
    MAX_CONTEXT_CHUNKS = 3
    
    # Maximum characters per chunk in context (truncate long chunks)
    MAX_CHUNK_LENGTH = 800
    
    # Maximum total context length (characters)
    MAX_CONTEXT_LENGTH = 3000
    
    # Phrases that indicate no relevant information was found
    NO_INFO_PHRASES = [
        "не мога да намеря",
        "не намерих",
        "няма информация",
        "не е налична информация",
        "не се споменава",
        "не е описан",
        "не е обяснен",
        "липсва информация",
        "не съдържа информация",
        "не открих",
        "не мога да отговоря",
        "не разполагам с информация",
    ]
    
    # Conversational patterns that should get direct responses (not RAG)
    CONVERSATIONAL_PATTERNS = {
        # Greetings and identity questions
        "как се казваш": "Аз съм IR Assistant - вашият помощник за курса по Information Retrieval. Как мога да ви помогна?",
        "кой си ти": "Аз съм IR Assistant - интелигентен асистент, създаден да помага с въпроси по Information Retrieval. Мога да отговарям на въпроси базирани на учебните материали.",
        "какво си ти": "Аз съм AI асистент, специализиран в помощ по курса Information Retrieval. Задайте ми въпрос по материала!",
        "представи се": "Здравейте! Аз съм IR Assistant - вашият помощник за курса по Information Retrieval. Мога да отговарям на въпроси по учебния материал и да генерирам тестови въпроси.",
        "здравей": "Здравейте! Как мога да ви помогна с Information Retrieval днес?",
        "здрасти": "Здравейте! Какъв въпрос по IR имате?",
        "привет": "Привет! Готов съм да помогна с въпроси по Information Retrieval.",
        "добър ден": "Добър ден! Как мога да ви бъда полезен?",
        "какво можеш": "Мога да:\n• Отговарям на въпроси по Information Retrieval базирани на учебния материал\n• Генерирам тестови въпроси (multiple choice и отворени)\n• Търся информация в лекциите\n\nЗадайте ми въпрос!",
        "какво правиш": "Помагам на студенти с въпроси по Information Retrieval! Имате ли въпрос по материала?",
        "благодаря": "Моля! Ако имате други въпроси по Information Retrieval, питайте!",
        "мерси": "Няма защо! Винаги съм тук да помогна с IR въпроси.",
    }
    
    # LLM generation options for faster inference
    LLM_OPTIONS = {
        "temperature": 0.3,
        "top_p": 0.9,
        "num_ctx": 4096,      # Reduced context window (faster)
        "num_predict": 512,   # Limit response length
    }
    
    def __init__(
        self, 
        model_name: str = "llama3.1:8b",
        retrieval_k: int = 5
    ):
        """
        Initialize RAG pipeline
        """
        self.model_name = model_name
        self.retrieval_k = retrieval_k
        self.retriever = get_retriever()
        self._validate_ollama_connection()
    
    def _validate_ollama_connection(self) -> None:
        """Validate Ollama connection on initialization"""
        try:
            ollama.list()
        except Exception as e:
            raise ConnectionError(
                f"Cannot connect to Ollama: {e}\n"
                "Make sure Ollama is running with: ollama serve"
            )
    
    def _check_conversational(self, question: str) -> str:
        """
        Check if the question is a conversational query (greeting, identity, etc.)
        Returns a direct response if it matches, None otherwise.
        """
        question_lower = question.lower().strip()
        
        # Remove punctuation for matching
        question_clean = ''.join(c for c in question_lower if c.isalnum() or c.isspace())
        question_clean = ' '.join(question_clean.split())
        
        for pattern, response in self.CONVERSATIONAL_PATTERNS.items():
            if pattern in question_clean or question_clean in pattern:
                return response
        
        return None
    
    def _filter_relevant_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Filter chunks by relevance score threshold.
        Only returns chunks that meet the minimum relevance score.
        """
        return [
            chunk for chunk in chunks 
            if chunk.get("score", 0) >= self.MIN_RELEVANCE_SCORE
        ]
    
    def _is_no_info_response(self, answer: str) -> bool:
        """
        Check if the LLM response indicates that no relevant information was found.
        """
        answer_lower = answer.lower()
        return any(phrase in answer_lower for phrase in self.NO_INFO_PHRASES)
    
    def _build_context(self, chunks: List[Dict]) -> str:
        """
        Build formatted context from retrieved chunks with source attribution.
        Limits context size for faster LLM processing.
        """
        # Limit number of chunks
        limited_chunks = chunks[:self.MAX_CONTEXT_CHUNKS]
        
        context_parts = []
        total_length = 0
        
        for i, chunk in enumerate(limited_chunks, 1):
            # Truncate long chunks
            text = chunk['text']
            if len(text) > self.MAX_CHUNK_LENGTH:
                text = text[:self.MAX_CHUNK_LENGTH] + "..."
            
            part = f"[Източник {i} - Страница {chunk['page']}, {chunk['section_title']}]\n{text}\n"
            
            # Check total context length
            if total_length + len(part) > self.MAX_CONTEXT_LENGTH:
                break
            
            context_parts.append(part)
            total_length += len(part)
        
        return "\n".join(context_parts)
    
    def _build_prompt(self, question: str, context: str, has_relevant_context: bool) -> tuple[str, str]:
        """
        Build prompt for the LLM
        """
        
        if has_relevant_context:
            system_instructions = """Ти си AI асистент, който помага на студенти с въпроси по Information Retrieval (Извличане на информация).
Твоята задача е да отговаряш на въпроси базирани САМО на предоставения контекст от учебния материал.

ПРАВИЛА:
1. Използвай САМО информацията от предоставения контекст
2. НЕ включвай източници, страници или препратки в отговора си - те се показват автоматично отделно
3. Ако контекстът НЕ съдържа информация, която директно отговаря на въпроса, кажи САМО "Не мога да намеря тази информация в предоставените материали."
4. Отговаряй на български език
5. Бъди прецизен и точен
6. Използвай примери от контекста, когато е възможно
7. НЕ измисляй информация, която не е в контекста
8. НЕ пиши "Източник:", "Source:", "Страница:" или подобни в отговора
"""

            user_prompt = f"""Контекст от учебния материал:
{context}

Въпрос на студента: {question}

Отговори на въпроса базирайки се на горния контекст. НЕ включвай препратки към страници или източници в отговора - те се показват автоматично отделно."""

        else:
            # No relevant context found - simpler prompt
            system_instructions = """Ти си AI асистент за курса по Information Retrieval."""
            
            user_prompt = f"""Въпрос на студента: {question}

За съжаление, не намерих релевантна информация за този въпрос в учебните материали. Моля, отговори САМО с: "Не мога да намеря тази информация в предоставените материали." """

        return system_instructions, user_prompt
    
    def answer_question(
        self, 
        question: str,
        retrieval_method: str = "hybrid",
        include_sources: bool = True
    ) -> Dict:
        """
        Answer a question using RAG pipeline
        """
        # Check for conversational queries first (greetings, identity, etc.)
        conversational_response = self._check_conversational(question)
        if conversational_response:
            return {
                "answer": conversational_response,
                "sources": [],
                "model": self.model_name,
                "retrieval_method": retrieval_method,
                "num_sources": 0
            }
        
        # Retrieve relevant chunks from lecture notes
        chunks = self.retriever.retrieve(
            question, 
            k=self.retrieval_k,
            method=retrieval_method
        )
        
        # Filter chunks by relevance score
        relevant_chunks = self._filter_relevant_chunks(chunks)
        has_relevant_context = len(relevant_chunks) > 0
        
        if not has_relevant_context:
            # No relevant chunks found - return immediately without sources
            return {
                "answer": "Не мога да намеря тази информация в предоставените материали.",
                "sources": [],
                "model": self.model_name,
                "retrieval_method": retrieval_method,
                "num_sources": 0
            }
        
        # Build formatted context and prompt
        context = self._build_context(relevant_chunks)
        system_instructions, user_prompt = self._build_prompt(question, context, has_relevant_context)
        
        # Generate answer with Ollama/Llama (optimized options for speed)
        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": user_prompt}
                ],
                options=self.LLM_OPTIONS
            )
            answer = response['message']['content']
            
        except Exception as e:
            answer = (
                f"Грешка при генериране на отговор: {str(e)}\n\n"
                f"Моля уверете се, че Ollama работи и моделът '{self.model_name}' е изтеглен."
            )
        
        # Check if the LLM response indicates no relevant information
        # In this case, don't include sources even if we had chunks
        if self._is_no_info_response(answer):
            return {
                "answer": "Не мога да намеря тази информация в предоставените материали.",
                "sources": [],
                "model": self.model_name,
                "retrieval_method": retrieval_method,
                "num_sources": 0
            }
        
        # Only include chunks that were actually used in context
        used_chunks = relevant_chunks[:self.MAX_CONTEXT_CHUNKS]
        
        # Build a structured response with sources
        result = {
            "answer": answer,
            "model": self.model_name,
            "retrieval_method": retrieval_method,
            "num_sources": len(used_chunks)
        }
        
        if include_sources:
            result["sources"] = [
                {
                    "chunk_id": chunk["chunk_id"],
                    "page": chunk["page"],
                    "section_title": chunk["section_title"],
                    "text": chunk["text"][:300] + "..." if len(chunk["text"]) > 300 else chunk["text"],
                    "score": chunk["score"]
                }
                for chunk in used_chunks
            ]
        
        return result
    
    def validate_question(self, question: str) -> Dict:
        """
        Validate and clean a user question
        """
        question = question.strip()
        
        if len(question) < 5:
            return {
                "valid": False,
                "reason": "Въпросът е твърде кратък",
                "cleaned_question": question
            }
        
        if len(question) > 500:
            return {
                "valid": False,
                "reason": "Въпросът е твърде дълъг",
                "cleaned_question": question[:500]
            }
        
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', question)
        
        return {
            "valid": True,
            "cleaned_question": cleaned,
            "original_question": question
        }


# Global RAG pipeline instance (Singleton pattern)
_rag_pipeline: Optional[RAGPipeline] = None


def get_rag_pipeline(model_name: str = "llama3.1:8b") -> RAGPipeline:
    """
    Get or create the global RAG pipeline instance (Singleton pattern)
    """
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline(model_name=model_name)
    return _rag_pipeline