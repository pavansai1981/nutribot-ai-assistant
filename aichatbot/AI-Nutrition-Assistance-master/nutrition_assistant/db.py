import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

# Configuration
RUN_TIMEZONE_CHECK = os.getenv('RUN_TIMEZONE_CHECK', '1') == '1'
TZ_INFO = os.getenv("TZ", "Europe/Berlin")
tz = ZoneInfo(TZ_INFO)

def get_db_connection():
    # Connects to a local file called nutrition.db
    conn = sqlite3.connect("nutrition.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS feedback")
        cur.execute("DROP TABLE IF EXISTS conversations")

        cur.execute("""
            CREATE TABLE conversations (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                model_used TEXT NOT NULL,
                response_time FLOAT NOT NULL,
                relevance TEXT NOT NULL,
                relevance_explanation TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                eval_prompt_tokens INTEGER NOT NULL,
                eval_completion_tokens INTEGER NOT NULL,
                eval_total_tokens INTEGER NOT NULL,
                openai_cost FLOAT NOT NULL,
                timestamp TIMESTAMP NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT REFERENCES conversations(id),
                feedback INTEGER NOT NULL,
                timestamp TIMESTAMP NOT NULL
            )
        """)
        conn.commit()
        print("Database initialized locally in nutrition.db")
    finally:
        conn.close()

def save_conversation(conversation_id, question, answer_data, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now(tz).isoformat()

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO conversations 
            (id, question, answer, model_used, response_time, relevance, 
            relevance_explanation, prompt_tokens, completion_tokens, total_tokens, 
            eval_prompt_tokens, eval_completion_tokens, eval_total_tokens, openai_cost, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                question,
                answer_data["answer"],
                answer_data["model_used"],
                answer_data["response_time"],
                answer_data["relevance"],
                answer_data["relevance_explanation"],
                answer_data["prompt_tokens"],
                answer_data["completion_tokens"],
                answer_data["total_tokens"],
                answer_data["eval_prompt_tokens"],
                answer_data["eval_completion_tokens"],
                answer_data["eval_total_tokens"],
                answer_data["openai_cost"],
                timestamp
            ),
        )
        conn.commit()
    finally:
        conn.close()

def save_feedback(conversation_id, feedback, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now(tz).isoformat()

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO feedback (conversation_id, feedback, timestamp) VALUES (?, ?, ?)",
            (conversation_id, feedback, timestamp),
        )
        conn.commit()
    finally:
        conn.close()

def get_recent_conversations(limit=5, relevance=None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        query = """
            SELECT c.*, f.feedback
            FROM conversations c
            LEFT JOIN feedback f ON c.id = f.conversation_id
        """
        params = []
        if relevance:
            query += " WHERE c.relevance = ?"
            params.append(relevance)
        
        query += " ORDER BY c.timestamp DESC LIMIT ?"
        params.append(limit)

        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def get_feedback_stats():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                SUM(CASE WHEN feedback > 0 THEN 1 ELSE 0 END) as thumbs_up,
                SUM(CASE WHEN feedback < 0 THEN 1 ELSE 0 END) as thumbs_down
            FROM feedback
        """)
        row = cur.fetchone()
        return {"thumbs_up": row[0] or 0, "thumbs_down": row[1] or 0}
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()