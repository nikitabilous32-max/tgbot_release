import sqlite3

conn = sqlite3.connect("messages.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 50")
rows = cur.fetchall()

for r in rows:
    print(dict(r))
