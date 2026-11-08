import os
import sqlite3
from datetime import datetime

# Ensure DB is created in the project directory regardless of execution CWD
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OLD_DB_NAME = os.path.join(BASE_DIR, "mitra_memory.db")
DB_NAME = os.path.join(BASE_DIR, "aurvyn_memory.db")

def init_db():
    """Creates the SQLite interactions table if it does not already exist."""
    try:
        if os.path.exists(OLD_DB_NAME) and not os.path.exists(DB_NAME):
            import shutil
            try:
                shutil.copy2(OLD_DB_NAME, DB_NAME)
            except Exception as e:
                print(f"[Database Migration Warning]: Could not copy old database: {e}")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_input TEXT NOT NULL,
                response TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Database Error]: Failed to initialize database: {e}")

def log_interaction(user_input: str, response: str):
    """Logs the user query and assistant response with an exact timestamp."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO interactions (timestamp, user_input, response) VALUES (?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_input, response)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Database Error]: Failed to log interaction: {e}")

def get_recent_interactions(limit: int = 5):
    """Retrieves the most recent interactions from the database."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT timestamp, user_input, response FROM interactions ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"[Database Error]: Failed to fetch recent interactions: {e}")
        return []

def get_total_interactions_count() -> int:
    """Returns total number of stored interactions in memory."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM interactions")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"[Database Error]: Failed to count interactions: {e}")
        return 0

def insert_interactions_batch(interactions: list) -> int:
    """
    Inserts a list of (timestamp, user_input, response) tuples into the database.
    Skips duplicates based on user_input and response to preserve memory integrity.
    Returns the number of new records successfully inserted.
    """
    if not interactions:
        return 0

    init_db()
    inserted_count = 0
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Load existing (user_input, response) pairs to avoid duplicate entries
        cursor.execute("SELECT user_input, response FROM interactions")
        existing_set = set((u.strip().lower(), r.strip().lower()) for u, r in cursor.fetchall())

        to_insert = []
        for item in interactions:
            if len(item) == 3:
                ts, u, r = item
            elif len(item) == 2:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                u, r = item
            else:
                continue

            u_clean = str(u).strip()
            r_clean = str(r).strip()
            if not u_clean or not r_clean:
                continue

            key = (u_clean.lower(), r_clean.lower())
            if key not in existing_set:
                existing_set.add(key)
                ts_str = str(ts).strip() if ts else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                to_insert.append((ts_str, u_clean, r_clean))

        if to_insert:
            cursor.executemany(
                "INSERT INTO interactions (timestamp, user_input, response) VALUES (?, ?, ?)",
                to_insert
            )
            conn.commit()
            inserted_count = len(to_insert)

        conn.close()
        return inserted_count
    except Exception as e:
        print(f"[Database Error]: Failed to batch insert interactions: {e}")
        return inserted_count