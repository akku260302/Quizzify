import sqlite3
import os

DB_PATH = "data/quiz.db"

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tests (
        test_id TEXT PRIMARY KEY,
        remarks TEXT,
        total_questions INTEGER,
        time_limit INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        question_id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_id TEXT,
        question_text TEXT,
        image_path TEXT,
        option_a TEXT,
        option_b TEXT,
        option_c TEXT,
        option_d TEXT,
        correct_option TEXT,
        FOREIGN KEY(test_id) REFERENCES tests(test_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS results (
        result_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        department TEXT,
        test_id TEXT,
        score INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS login_control (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        is_enabled INTEGER DEFAULT 0,
        enabled_at TIMESTAMP
    )
    """)

    # Ensure one row exists in login_control
    cursor.execute("INSERT OR IGNORE INTO login_control (id, is_enabled) VALUES (1, 0)")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    if not os.path.exists("data"):
        os.makedirs("data")
    init_db()
    print("Database initialized!")