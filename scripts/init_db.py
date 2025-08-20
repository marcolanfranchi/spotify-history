import os
import sqlite3
from pathlib import Path

DB_NAME = os.getenv("SQLITE_DB_NAME", "plays.db")
DB_PATH = Path(f"db/{DB_NAME}")

# Find the latest schema version in db/sql/
schema_files = sorted(Path("db/sql").glob("V*__*.sql"), reverse=True)
if not schema_files:
    raise FileNotFoundError("No schema files found in db/sql/")
SCHEMA_PATH = schema_files[0]

if not DB_PATH.exists():
    print("Creating SQLite DB and tables...")
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA_PATH.read_text())
    print("DB ready! ✅")
else:
    print(f"SQLite DB already exists at {DB_PATH}. Applying latest schema...")
    with sqlite3.connect(DB_PATH) as conn:
        print(SCHEMA_PATH.read_text())
        conn.executescript(SCHEMA_PATH.read_text())
    print("Schema applied! ✅")

