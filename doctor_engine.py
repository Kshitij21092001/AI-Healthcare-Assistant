# doctor_engine.py
import sqlite3

DB_PATH = "doctors.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Create table
    c.execute("""
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        specialty TEXT NOT NULL,
        contact TEXT,
        email TEXT,
        UNIQUE(name, specialty) 
    )
    """)
    conn.commit()
    conn.close()

def add_doctor(name, specialty, contact="", email=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Check if doctor already exists to prevent duplicates
    c.execute("SELECT id FROM doctors WHERE name = ? AND specialty = ?", (name, specialty))
    data = c.fetchone()

    if data is None:
        c.execute(
            "INSERT INTO doctors (name, specialty, contact, email) VALUES (?, ?, ?, ?)",
            (name, specialty, contact, email)
        )
        print(f"Added {name}")
    else:
        print(f"Skipped {name} (Already exists)")

    conn.commit()
    conn.close()

def get_doctors_by_specialty(specialty):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, specialty, contact, email FROM doctors WHERE specialty LIKE ?", (f"%{specialty}%",))
    rows = c.fetchall()
    conn.close()
    return [{"name": r[0], "specialty": r[1], "contact": r[2], "email": r[3]} for r in rows]