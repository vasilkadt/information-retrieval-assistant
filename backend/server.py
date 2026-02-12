"""
FastAPI Backend Server
REST API for the Information Retrieval Assistant
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import uuid
from datetime import datetime, timezone
from rag import get_rag_pipeline
from question_generator import get_question_generator
from database import get_db
from language_validator import get_validator

# Initialize FastAPI app
app = FastAPI(
    title="Information Retrieval Assistant API",
    description="RAG-based chatbot for answering questions about IR course material",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=500)
    session_id: Optional[str] = None
    retrieval_method: str = Field(default="hybrid", pattern="^(hybrid|bm25|vector)$")
    model: str = Field(default="llama3.1:8b")

class QuestionResponse(BaseModel):
    answer: str
    sources: List[Dict]
    model: str
    retrieval_method: str
    num_sources: int
    chat_id: int
    session_id: str

class GenerateQuestionsRequest(BaseModel):
    question_type: str = Field(..., pattern="^(multiple_choice|open_ended)$")
    num_questions: int = Field(default=5, ge=1, le=20)
    section: Optional[str] = None
    difficulty: Optional[str] = Field(default="medium", pattern="^(easy|medium|hard)$")

class FeedbackRequest(BaseModel):
    chat_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

# Global instances
rag_pipeline = None
question_generator = None
db = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global rag_pipeline, question_generator, db
    
    print("🚀 Starting Information Retrieval Assistant...")
    
    # Initialize database
    db = get_db()
    print("✓ Database initialized")
    
    # Initialize RAG pipeline
    try:
        rag_pipeline = get_rag_pipeline()
        print("✓ RAG pipeline initialized")
    except Exception as e:
        print(f"⚠ Warning: Could not initialize RAG pipeline: {e}")
    
    # Initialize question generator
    try:
        question_generator = get_question_generator()
        print("✓ Question generator initialized")
    except Exception as e:
        print(f"⚠ Warning: Could not initialize question generator: {e}")
    
    print("✓ Server ready!")

# Health check
@app.get("/")
async def root():
    return {
        "message": "Information Retrieval Assistant API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "database": db is not None,
            "rag_pipeline": rag_pipeline is not None,
            "question_generator": question_generator is not None
        }
    }

# Question answering
@app.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask a question and get an answer using RAG
    
    Note: This chatbot only supports the Bulgarian language.
    Questions in other languages will be rejected.
    """
    if rag_pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="RAG pipeline not initialized. Make sure Ollama is running."
        )
    
    # Validate language (Bulgarian only)
    validator = get_validator()
    validation_result = validator.validate(request.question)
    
    if not validation_result["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "language_not_supported",
                "message": validation_result["message"],
                "detected_language": validation_result["language"],
                "supported_language": "български (Bulgarian)"
            }
        )
    
    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        # Get answer from the RAG pipeline
        result = rag_pipeline.answer_question(
            question=request.question,
            retrieval_method=request.retrieval_method,
            include_sources=True
        )
        
        # Save to a database
        chat_id = db.save_chat(
            question=request.question,
            answer=result["answer"],
            sources=result.get("sources", []),
            model=result["model"],
            retrieval_method=result["retrieval_method"],
            session_id=session_id
        )
        
        return QuestionResponse(
            answer=result["answer"],
            sources=result.get("sources", []),
            model=result["model"],
            retrieval_method=result["retrieval_method"],
            num_sources=result["num_sources"],
            chat_id=chat_id,
            session_id=session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Retrieval only (no generation)
@app.get("/search")
async def search(
    q: str = Query(..., min_length=3),
    method: str = Query(default="hybrid", pattern="^(hybrid|bm25|vector)$"),
    k: int = Query(default=5, ge=1, le=20)
):
    """
    Search for relevant chunks without generating an answer
    """
    if rag_pipeline is None:
        raise HTTPException(status_code=503, detail="Retrieval system not initialized")
    
    try:
        chunks = rag_pipeline.retriever.retrieve(q, k=k, method=method)
        return {
            "query": q,
            "method": method,
            "results": chunks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Question generation
@app.post("/generate-questions")
async def generate_questions(request: GenerateQuestionsRequest):
    """
    Generate test questions
    """
    if question_generator is None:
        raise HTTPException(status_code=503, detail="Question generator not initialized")
    
    try:
        if request.question_type == "multiple_choice":
            questions = await question_generator.generate_multiple_choice_async(
                section=request.section,
                num_questions=request.num_questions,
                difficulty=request.difficulty
            )
        else:  # open_ended
            questions = await question_generator.generate_open_ended_async(
                section=request.section,
                num_questions=request.num_questions,
                difficulty=request.difficulty
            )
        
        if not questions:
            return {
                "questions": [],
                "count": 0,
                "type": request.question_type,
                "message": "No questions could be generated. Please try again."
            }
        
        # Save to database with error handling
        saved_count = 0
        for q in questions:
            try:
                db.save_generated_question(q)
                saved_count += 1
            except Exception as save_error:
                print(f"Error saving question to database: {save_error}")
        
        return {
            "questions": questions,
            "count": len(questions),
            "type": request.question_type
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating questions: {str(e)}")

# Get generated questions
@app.get("/questions")
async def get_questions(
    type: Optional[str] = Query(None, pattern="^(multiple_choice|open_ended)$"),
    limit: int = Query(default=50, ge=1, le=200)
):
    """
    Get previously generated questions from a database
    """
    try:
        questions = db.get_generated_questions(
            question_type=type,
            limit=limit
        )
        return {
            "questions": questions,
            "count": len(questions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Chat history
@app.get("/history")
async def get_history(
    session_id: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200)
):
    """
    Get chat history
    """
    try:
        history = db.get_chat_history(session_id=session_id, limit=limit)
        return {
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Feedback
@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    Submit feedback for a chat response
    """
    try:
        db.save_feedback(
            chat_id=request.chat_id,
            rating=request.rating,
            comment=request.comment
        )
        return {"message": "Feedback saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Statistics
@app.get("/stats")
async def get_stats():
    """
    Get system statistics
    """
    try:
        stats = db.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Validate question
@app.post("/validate")
async def validate_question(question: str):
    """
    Validate and clean a question
    """
    if rag_pipeline is None:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    
    result = rag_pipeline.validate_question(question)
    return result


# ── Topic Summary ──────────────────────────────────────────────────

class SummaryRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=200)
    detail_level: str = Field(default="medium", pattern="^(brief|medium|detailed)$")

@app.post("/summarize")
async def summarize_topic(request: SummaryRequest):
    """Generate a summary for a given topic from the course material"""
    if rag_pipeline is None:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    
    try:
        # Retrieve relevant chunks for the topic
        chunks = rag_pipeline.retriever.retrieve(request.topic, k=8, method="hybrid")
        
        if not chunks:
            return {
                "summary": "Не намерих информация по тази тема в материалите.",
                "topic": request.topic,
                "pages": [],
                "sections": []
            }
        
        # Build context
        context = "\n\n".join(
            f"[Стр. {c['page']}] {c['text'][:500]}" for c in chunks
        )
        
        detail_map = {
            "brief": "2-3 изречения",
            "medium": "1 параграф (5-7 изречения)",
            "detailed": "подробно обяснение с примери (10-15 изречения)"
        }
        
        import ollama
        response = ollama.chat(
            model="llama3.1:8b",
            messages=[
                {"role": "system", "content": "Ти си AI асистент за курс по Information Retrieval. Генерирай кратко и ясно резюме на български език."},
                {"role": "user", "content": f"""Контекст:\n{context}\n\nГенерирай резюме на тема "{request.topic}" с дължина {detail_map.get(request.detail_level, '1 параграф')}.\n\nВключи ключовите концепции и важни детайли. Отговори на български."""}
            ],
            options={"temperature": 0.3, "num_ctx": 4096, "num_predict": 1024}
        )
        
        pages = sorted(set(c["page"] for c in chunks))
        sections = list(set(c["section_title"] for c in chunks))
        
        return {
            "summary": response["message"]["content"],
            "topic": request.topic,
            "detail_level": request.detail_level,
            "pages": pages,
            "sections": sections,
            "num_sources": len(chunks)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Flashcards ─────────────────────────────────────────────────────

class FlashcardsRequest(BaseModel):
    num_cards: int = Field(default=6, ge=1, le=20)
    category: Optional[str] = None


@app.post("/flashcards")
async def get_flashcards(request: FlashcardsRequest):
    """Get random flashcards from the pre-built pool"""
    try:
        pool_count = db.get_flashcard_count()
        
        # Auto-populate pool from existing questions if empty
        if pool_count == 0:
            added = db.populate_flashcards_from_questions()
            pool_count = db.get_flashcard_count()
        
        cards = db.get_flashcards(count=request.num_cards, category=request.category)
        
        return {
            "flashcards": cards,
            "count": len(cards),
            "pool_size": pool_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/flashcards/generate")
async def generate_more_flashcards(count: int = 10):
    """Generate new flashcards and add them to the pool using the question generator"""
    if question_generator is None:
        raise HTTPException(status_code=503, detail="Question generator not initialized")
    
    try:
        added = 0
        
        # First: import any existing questions that aren't in the pool yet
        from_existing = db.populate_flashcards_from_questions()
        added += from_existing
        
        # Then: generate new MCQ questions and convert them to flashcards
        if added < count:
            needed = count - added
            # Generate MCQ questions (they have the best structure for flashcards)
            for difficulty in ["easy", "medium", "hard"]:
                if added >= count:
                    break
                batch = min(needed, 5)
                try:
                    result = await question_generator.generate_multiple_choice_async(
                        num_questions=batch, difficulty=difficulty
                    )
                    questions = result.get("questions", [])
                    
                    for q in questions:
                        options = q.get("options", [])
                        correct_idx = q.get("correct_answer", 0)
                        correct_text = options[correct_idx] if 0 <= correct_idx < len(options) else ""
                        explanation = q.get("explanation", "")
                        
                        back = f"✅ {correct_text}"
                        if explanation:
                            back += f"\n\n📝 {explanation}"
                        
                        result_id = db.save_flashcard(
                            front=q.get("question", ""),
                            back=back.strip(),
                            hint=f"Избери от: {', '.join(options[:2])}..." if len(options) > 2 else "",
                            category="Тестови въпроси",
                            page=q.get("page", 0),
                            section=q.get("section", ""),
                            source_type="multiple_choice",
                            source_id=0
                        )
                        if result_id > 0:
                            added += 1
                except Exception:
                    continue
            
            # Generate open-ended questions
            if added < count:
                try:
                    result = await question_generator.generate_open_ended_async(
                        num_questions=min(count - added, 5), difficulty="medium"
                    )
                    questions = result.get("questions", [])
                    
                    for q in questions:
                        import json as _json
                        sample = q.get("sample_answer", "")
                        key_pts = q.get("key_points", [])
                        
                        back = sample if sample else ""
                        if key_pts:
                            back += "\n\n🔑 Ключови точки:\n" + "\n".join(f"• {p}" for p in key_pts)
                        
                        result_id = db.save_flashcard(
                            front=q.get("question", ""),
                            back=back.strip(),
                            hint=f"Помисли за: {key_pts[0]}" if key_pts else "",
                            category="Отворени въпроси",
                            page=q.get("page", 0),
                            section=q.get("section", ""),
                            source_type="open_ended",
                            source_id=0
                        )
                        if result_id > 0:
                            added += 1
                except Exception:
                    pass
        
        pool_count = db.get_flashcard_count()
        return {
            "added": added,
            "pool_size": pool_count,
            "message": f"Добавени {added} нови флашкарти. Общо в пула: {pool_count}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/flashcards/pool")
async def flashcard_pool_info():
    """Get info about the flashcard pool"""
    try:
        count = db.get_flashcard_count()
        categories = db.get_flashcard_categories()
        return {
            "pool_size": count,
            "categories": categories
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Available Topics ───────────────────────────────────────────────

@app.get("/topics")
async def get_topics():
    """Get list of available topics/sections from the material"""
    if rag_pipeline is None:
        raise HTTPException(status_code=503, detail="Not initialized")
    
    try:
        chunks = rag_pipeline.retriever.chunks
        sections = {}
        for chunk in chunks:
            sec = chunk.get("section_title", "Unknown")
            if sec != "Unknown":
                if sec not in sections:
                    sections[sec] = {"title": sec, "page": chunk["page"], "chunks": 0}
                sections[sec]["chunks"] += 1
        
        topics = sorted(sections.values(), key=lambda x: x["page"])
        return {"topics": topics, "count": len(topics)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
