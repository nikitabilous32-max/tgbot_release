import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "messages.db")

def fix_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        cur.execute("ALTER TABLE messages ADD COLUMN file_unique_id TEXT;")
        print("file_unique_id добавлен")
    except Exception as e:
        print("file_unique_id уже существует:", e)

    try:
        cur.execute("ALTER TABLE messages ADD COLUMN local_path TEXT;")
        print("local_path добавлен")
    except Exception as e:
        print("local_path уже существует:", e)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    fix_db()
