"""
Database Module
SQLite database for storing questions, answers, and chat history
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

DB_PATH = Path(__file__).parent.parent / "data" / "assistant.db"

class Database:
    """SQLite database for the assistant"""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Chat history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                sources TEXT,
                model TEXT,
                retrieval_method TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Generated questions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generated_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_type TEXT NOT NULL,
                question TEXT NOT NULL,
                options TEXT,
                correct_answer INTEGER,
                explanation TEXT,
                key_points TEXT,
                sample_answer TEXT,
                difficulty TEXT,
                page INTEGER,
                section TEXT,
                chunk_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # User feedback table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                rating INTEGER,
                comment TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chat_history(id)
            )
        """)
        
        conn.commit()
        conn.close()
        
        print(f"✓ Database initialized: {self.db_path}")
    
    def save_chat(
        self,
        question: str,
        answer: str,
        sources: List[Dict],
        model: str,
        retrieval_method: str,
        session_id: Optional[str] = None
    ) -> int:
        """Save a chat interaction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO chat_history 
            (session_id, question, answer, sources, model, retrieval_method)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            question,
            answer,
            json.dumps(sources, ensure_ascii=False),
            model,
            retrieval_method
        ))
        
        chat_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return chat_id
    
    def get_chat_history(
        self,
        session_id: Optional[str] = None, 
        limit: int = 50
    ) -> List[Dict]:
        """Get chat history"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if session_id:
            cursor.execute("""
                SELECT * FROM chat_history 
                WHERE session_id = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (session_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM chat_history 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def save_generated_question(self, question_data: Dict) -> int:
        """Save a generated question"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO generated_questions
            (question_type, question, options, correct_answer, explanation,
             key_points, sample_answer, difficulty, page, section, chunk_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            question_data.get("type"),
            question_data.get("question"),
            json.dumps(question_data.get("options"), ensure_ascii=False) 
                if question_data.get("options") else None,
            question_data.get("correct_answer"),
            question_data.get("explanation"),
            json.dumps(question_data.get("key_points"), ensure_ascii=False)
                if question_data.get("key_points") else None,
            question_data.get("sample_answer"),
            question_data.get("difficulty"),
            question_data.get("page"),
            question_data.get("section"),
            question_data.get("chunk_id")
        ))
        
        question_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return question_id
    
    def get_generated_questions(
        self,
        question_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get generated questions"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if question_type:
            cursor.execute("""
                SELECT * FROM generated_questions
                WHERE question_type = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (question_type, limit))
        else:
            cursor.execute("""
                SELECT * FROM generated_questions
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            data = dict(row)
            if data.get('options'):
                data['options'] = json.loads(data['options'])
            if data.get('key_points'):
                data['key_points'] = json.loads(data['key_points'])
            result.append(data)
        
        return result
    
    def save_feedback(
        self,
        chat_id: int,
        rating: int,
        comment: Optional[str] = None
    ):
        """Save user feedback"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO feedback (chat_id, rating, comment)
            VALUES (?, ?, ?)
        """, (chat_id, rating, comment))
        
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}

        cursor.execute("SELECT COUNT(*) FROM chat_history")
        stats['total_chats'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM generated_questions")
        stats['total_generated_questions'] = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT question_type, COUNT(*) as count
            FROM generated_questions
            GROUP BY question_type
        """)
        stats['questions_by_type'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute("SELECT AVG(rating) FROM feedback")
        avg_rating = cursor.fetchone()[0]
        stats['average_rating'] = round(avg_rating, 2) if avg_rating else None
        
        conn.close()
        
        return stats

# Global database instance
_db = None

def get_db() -> Database:
    """Get or create the global database instance"""
    global _db
    if _db is None:
        _db = Database()
    return _db
