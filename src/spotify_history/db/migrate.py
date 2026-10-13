"""Apply SQL migrations from migrations/ (V<version>__<name>.sql) in version order.

Applied versions are tracked in `schema_migrations`. A database created before that
table existed only ever had V1, so it is baselined to V1 instead of being re-run.
"""
import re
import sqlite3
from pathlib import Path

from spotify_history import config

_MIGRATION_RE = re.compile(r"^V(\d+)__.+\.sql$")


def _discover(migrations_dir):
    found = []
    for path in Path(migrations_dir).glob("V*__*.sql"):
        match = _MIGRATION_RE.match(path.name)
        if match:
            found.append((int(match.group(1)), path))
    return sorted(found)


def _check_legacy_location(db_path):
    if (
        db_path == config.DB_PATH
        and not db_path.exists()
        and config.LEGACY_DB_PATH.exists()
    ):
        raise SystemExit(
            f"Found an existing database at {config.LEGACY_DB_PATH} but none at {db_path}.\n"
            f"Move it first so history is preserved:\n"
            f"  mkdir -p {db_path.parent} && mv {config.LEGACY_DB_PATH} {db_path}"
        )


def migrate(db_path=None, migrations_dir=None):
    db_path = Path(db_path or config.DB_PATH)
    migrations_dir = migrations_dir or config.MIGRATIONS_DIR

    migrations = _discover(migrations_dir)
    if not migrations:
        raise FileNotFoundError(f"No migration files found in {migrations_dir}")

    _check_legacy_location(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version INTEGER PRIMARY KEY, "
            "applied_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
        )
        applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}

        if not applied:
            has_plays = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='plays'"
            ).fetchone()
            if has_plays:
                conn.execute("INSERT INTO schema_migrations (version) VALUES (1)")
                conn.commit()
                applied.add(1)
                print("Existing database detected; baselined at V1.")

        pending = [(v, p) for v, p in migrations if v not in applied]
        if not pending:
            print(f"Database up to date at {db_path} (V{max(applied)}).")
            return

        for version, path in pending:
            print(f"Applying {path.name}...")
            conn.executescript(path.read_text())
            conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
            conn.commit()
        print(f"Database ready at {db_path} (V{pending[-1][0]}).")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
