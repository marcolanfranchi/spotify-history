import os
import sqlite3
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()

DB_NAME = os.getenv("SQLITE_DB_NAME", "plays.db")
DB_PATH = os.path.join("db", DB_NAME)

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
