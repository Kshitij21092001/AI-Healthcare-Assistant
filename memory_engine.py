# memory_engine.py
import sqlite3
from datetime import datetime

DB = "chat_memory.db"

def init_memory_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,    -- user | assistant | system
        content TEXT NOT NULL,
        ts TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()

def add_message(role, content):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO messages (role, content, ts) VALUES (?, ?, ?)",
              (role, content, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_recent(n=20):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT role, content, ts FROM messages ORDER BY id DESC LIMIT ?", (n,))
    rows = c.fetchall()
    conn.close()
    # return in chronological order
    return [{"role": r[0], "content": r[1], "ts": r[2]} for r in reversed(rows)]
