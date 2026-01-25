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
    
    def _build_context(self, chunks: List[Dict]) -> str:
        """
        Build formatted context from retrieved chunks with source attribution
        """
        context_parts = [
            f"[Източник {i} - Страница {chunk['page']}, {chunk['section_title']}]\n"
            f"{chunk['text']}\n"
            for i, chunk in enumerate(chunks, 1)
        ]
        return "\n".join(context_parts)
    
    def _build_prompt(self, question: str, context: str) -> tuple[str, str]:
        """
        Build prompt for the LLM
        """
        
        system_instructions = """Ти си AI асистент, който помага на студенти с въпроси по Information Retrieval (Извличане на информация).
Твоята задача е да отговаряш на въпроси базирани САМО на предоставения контекст от учебния материал.

ПРАВИЛА:
1. Използвай САМО информацията от предоставения контекст
2. Винаги посочвай източниците (страници и секции) в отговора си
3. Ако информацията не е в контекста, кажи "Не мога да намеря тази информация в предоставените материали"
4. Отговаряй на български език
5. Бъди прецизен и точен
6. Използвай примери от контекста, когато е възможно
"""

        user_prompt = f"""Контекст от учебния материал:
{context}

Въпрос на студента: {question}

Моля, отговори на въпроса базирайки се на горния контекст. Включи препратки към страниците и секциите, откъдето взимаш информацията."""

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
        # Retrieve relevant chunks from lecture notes
        chunks = self.retriever.retrieve(
            question, 
            k=self.retrieval_k,
            method=retrieval_method
        )
        
        if not chunks:
            return {
                "answer": "Не намерих релевантна информация за този въпрос в материалите.",
                "sources": [],
                "model": self.model_name
            }
        
        # Build formatted context and prompt
        context = self._build_context(chunks)
        system_instructions, user_prompt = self._build_prompt(question, context)
        
        # Generate answer with Ollama/Llama
        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": user_prompt}
                ],
                options={
                    "temperature": 0.3,
                    "top_p": 0.9,
                }
            )
            answer = response['message']['content']
            
        except Exception as e:
            answer = (
                f"Грешка при генериране на отговор: {str(e)}\n\n"
                f"Моля уверете се, че Ollama работи и моделът '{self.model_name}' е изтеглен."
            )
        
        # Build a structured response
        result = {
            "answer": answer,
            "model": self.model_name,
            "retrieval_method": retrieval_method,
            "num_sources": len(chunks)
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
                for chunk in chunks
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