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
        
        # Question cache table for fast retrieval
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS question_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT UNIQUE NOT NULL,
                question_type TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                question_data TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Index for fast cache lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cache_lookup 
            ON question_cache(question_type, difficulty)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cache_key 
            ON question_cache(cache_key)
        """)
        
        # Flashcard pool table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flashcard_pool (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                front TEXT NOT NULL,
                back TEXT NOT NULL,
                hint TEXT,
                category TEXT,
                page INTEGER,
                section TEXT,
                source_type TEXT,
                source_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_flashcard_category 
            ON flashcard_pool(category)
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
    
    def cache_question(self, cache_key: str, question_type: str, 
                       difficulty: str, chunk_id: str, question_data: Dict) -> None:
        """Cache a generated question for fast future retrieval"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO question_cache 
            (cache_key, question_type, difficulty, chunk_id, question_data)
            VALUES (?, ?, ?, ?, ?)
        """, (
            cache_key,
            question_type,
            difficulty,
            chunk_id,
            json.dumps(question_data, ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()
    
    def get_cached_questions(self, question_type: str, difficulty: str, 
                             limit: int = 20) -> List[Dict]:
        """Get cached questions by type and difficulty"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT question_data FROM question_cache
            WHERE question_type = ? AND difficulty = ?
            ORDER BY RANDOM()
            LIMIT ?
        """, (question_type, difficulty, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [json.loads(row[0]) for row in rows]
    
    def get_cache_count(self, question_type: str, difficulty: str) -> int:
        """Get number of cached questions for a type+difficulty"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM question_cache
            WHERE question_type = ? AND difficulty = ?
        """, (question_type, difficulty))
        
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def is_question_cached(self, cache_key: str) -> bool:
        """Check if a question with this cache key already exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT 1 FROM question_cache WHERE cache_key = ?", 
            (cache_key,)
        )
        
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    
    # ── Flashcard Pool ───────────────────────────────────────────────

    def save_flashcard(self, front: str, back: str, hint: str = "",
                       category: str = "", page: int = 0, section: str = "",
                       source_type: str = "", source_id: int = 0) -> int:
        """Save a flashcard to the pool"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check for duplicates (same front text)
        cursor.execute(
            "SELECT id FROM flashcard_pool WHERE front = ?", (front,)
        )
        if cursor.fetchone():
            conn.close()
            return -1
        
        cursor.execute("""
            INSERT INTO flashcard_pool 
            (front, back, hint, category, page, section, source_type, source_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (front, back, hint, category, page, section, source_type, source_id))
        
        fid = cursor.lastrowid
        conn.commit()
        conn.close()
        return fid

    def get_flashcards(self, count: int = 10, category: str = None) -> List[Dict]:
        """Get random flashcards from the pool"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if category:
            cursor.execute("""
                SELECT * FROM flashcard_pool 
                WHERE category = ?
                ORDER BY RANDOM() LIMIT ?
            """, (category, count))
        else:
            cursor.execute("""
                SELECT * FROM flashcard_pool 
                ORDER BY RANDOM() LIMIT ?
            """, (count,))
        
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_flashcard_count(self) -> int:
        """Get total number of flashcards in pool"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM flashcard_pool")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_flashcard_categories(self) -> List[Dict]:
        """Get flashcard categories with counts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT category, COUNT(*) as count 
            FROM flashcard_pool 
            WHERE category IS NOT NULL AND category != ''
            GROUP BY category
            ORDER BY count DESC
        """)
        cats = [{"category": row[0], "count": row[1]} for row in cursor.fetchall()]
        conn.close()
        return cats

    def populate_flashcards_from_questions(self) -> int:
        """Convert existing generated questions into flashcards"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all generated questions
        cursor.execute("SELECT * FROM generated_questions")
        questions = [dict(r) for r in cursor.fetchall()]
        conn.close()
        
        added = 0
        for q in questions:
            qtype = q["question_type"]
            front = q["question"]
            
            if qtype == "multiple_choice":
                # Build the answer from correct option + explanation
                options = json.loads(q["options"]) if q["options"] else []
                correct_idx = q.get("correct_answer", 0)
                correct_text = options[correct_idx] if 0 <= correct_idx < len(options) else ""
                explanation = q.get("explanation", "")
                
                back = f"✅ {correct_text}"
                if explanation:
                    back += f"\n\n📝 {explanation}"
                hint = f"Избери от: {', '.join(options[:2])}..." if len(options) > 2 else ""
                category = "Тестови въпроси"
            else:
                # Open-ended: use sample_answer + key_points
                sample = q.get("sample_answer", "")
                key_pts = json.loads(q["key_points"]) if q.get("key_points") else []
                
                back = sample if sample else ""
                if key_pts:
                    back += "\n\n🔑 Ключови точки:\n" + "\n".join(f"• {p}" for p in key_pts)
                hint = f"Помисли за: {key_pts[0]}" if key_pts else ""
                category = "Отворени въпроси"
            
            if front and back:
                result = self.save_flashcard(
                    front=front,
                    back=back.strip(),
                    hint=hint,
                    category=category,
                    page=q.get("page", 0),
                    section=q.get("section", ""),
                    source_type=qtype,
                    source_id=q["id"]
                )
                if result > 0:
                    added += 1
        
        return added

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
        
        cursor.execute("SELECT COUNT(*) FROM feedback")
        stats['total_feedback'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM question_cache")
        stats['cached_questions'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM flashcard_pool")
        stats['total_flashcards'] = cursor.fetchone()[0]
        
        # Retrieval methods breakdown
        cursor.execute("""
            SELECT retrieval_method, COUNT(*) as count
            FROM chat_history
            WHERE retrieval_method IS NOT NULL
            GROUP BY retrieval_method
        """)
        stats['retrieval_methods'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Daily activity (last 7 days)
        cursor.execute("""
            SELECT DATE(timestamp) as day, COUNT(*) as count
            FROM chat_history
            WHERE timestamp >= DATE('now', '-7 days')
            GROUP BY DATE(timestamp)
            ORDER BY day ASC
        """)
        stats['daily_activity'] = [{"date": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        # Questions by difficulty
        cursor.execute("""
            SELECT difficulty, COUNT(*) as count
            FROM generated_questions
            WHERE difficulty IS NOT NULL
            GROUP BY difficulty
        """)
        stats['questions_by_difficulty'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Top sections asked about
        cursor.execute("""
            SELECT section, COUNT(*) as count
            FROM generated_questions
            WHERE section IS NOT NULL AND section != ''
            GROUP BY section
            ORDER BY count DESC
            LIMIT 8
        """)
        stats['top_sections'] = [{"section": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        # Recent questions (last 5)
        cursor.execute("""
            SELECT question, timestamp FROM chat_history
            ORDER BY timestamp DESC LIMIT 5
        """)
        stats['recent_questions'] = [{"question": row[0][:80], "time": row[1]} for row in cursor.fetchall()]
        
        # Rating distribution
        cursor.execute("""
            SELECT rating, COUNT(*) as count
            FROM feedback
            WHERE rating IS NOT NULL
            GROUP BY rating
            ORDER BY rating
        """)
        stats['rating_distribution'] = {str(row[0]): row[1] for row in cursor.fetchall()}
        
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
