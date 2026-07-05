import sqlite3
import os

# Абсолютный путь к messages.db вне папок ботов
DB_PATH = os.path.join(os.path.dirname(__file__), "messages.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        message_id INTEGER,
        user_id INTEGER,
        username TEXT,
        date INTEGER,
        text TEXT,
        media_type TEXT,
        file_id TEXT,
        file_unique_id TEXT,
        local_path TEXT,
        deleted INTEGER DEFAULT 0,
        edited INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()

init_db()
