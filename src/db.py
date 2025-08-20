import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()

DB_NAME = os.getenv("SQLITE_DB_NAME", "plays.db")
if os.path.exists(f"./db/{DB_NAME}"):
    DB_PATH = f"./db/{DB_NAME}"
else:
    DB_PATH = f"spotify-history/db/{DB_NAME}"

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # enforce foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

