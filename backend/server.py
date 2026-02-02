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
            questions = question_generator.generate_multiple_choice(
                section=request.section,
                num_questions=request.num_questions,
                difficulty=request.difficulty
            )
        else:  # open_ended
            questions = question_generator.generate_open_ended(
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
