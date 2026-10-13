import sqlite3

import pytest

from spotify_history import config
from spotify_history.db.migrate import migrate


def _tables(path):
    with sqlite3.connect(path) as conn:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_fresh_database_gets_schema(tmp_path):
    path = tmp_path / "plays.db"
    migrate(db_path=path)
    assert {"users", "plays", "schema_migrations"} <= _tables(path)


def test_migrate_is_idempotent(tmp_path):
    path = tmp_path / "plays.db"
    migrate(db_path=path)
    migrate(db_path=path)
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT version FROM schema_migrations").fetchall() == [(1,), (2,)]


def test_pre_existing_database_is_baselined_and_data_kept(tmp_path):
    """A DB created by the old init_db.py (no schema_migrations table) keeps its rows."""
    path = tmp_path / "plays.db"
    with sqlite3.connect(path) as conn:
        conn.executescript((config.MIGRATIONS_DIR / "V1__create_schema.sql").read_text())
        conn.execute("INSERT INTO users (spotify_user_id) VALUES ('u1')")
        conn.execute(
            "INSERT INTO plays (user_id, track_id, track_name, artist_id, artist_name, played_at)"
            " VALUES (1, 't1', 'Song', 'a1', 'Artist', '2025-08-19T20:57:21.365Z')"
        )

    migrate(db_path=path)

    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM plays").fetchone()[0] == 1
        assert conn.execute("SELECT version FROM schema_migrations").fetchall() == [(1,), (2,)]


def test_refuses_to_create_new_db_when_legacy_db_exists(tmp_path, monkeypatch):
    legacy = tmp_path / "db" / "plays.db"
    legacy.parent.mkdir()
    legacy.touch()
    new = tmp_path / "data" / "plays.db"
    monkeypatch.setattr(config, "DB_PATH", new)
    monkeypatch.setattr(config, "LEGACY_DB_PATH", legacy)

    with pytest.raises(SystemExit):
        migrate(db_path=new)
    assert not new.exists()


def _v1_database_with_plays(path):
    with sqlite3.connect(path) as conn:
        conn.executescript((config.MIGRATIONS_DIR / "V1__create_schema.sql").read_text())
        conn.execute("INSERT INTO users (spotify_user_id) VALUES ('u1')")
        rows = [
            # (track, track_name, artist, artist_name, album, album_name, played_at)
            ("t1", "Song", "a1", "Old Name", "al1", "Album", "2025-01-01T00:00:00.000Z"),
            ("t1", "Song", "a1", "New Name", "al1", "Album", "2025-02-01T00:00:00.000Z"),
            ("t2", "Other", "a2", "Second", None, None, "2025-03-01T00:00:00.000Z"),
        ]
        for t, tn, a, an, al, aln, at in rows:
            conn.execute(
                "INSERT INTO plays (user_id, track_id, track_name, artist_id, artist_name,"
                " album_id, album_name, played_at, duration_ms) VALUES (1,?,?,?,?,?,?,?,1000)",
                (t, tn, a, an, al, aln, at),
            )


def test_v2_seeds_entity_tables_from_existing_plays(tmp_path):
    path = tmp_path / "plays.db"
    _v1_database_with_plays(path)

    migrate(db_path=path)

    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM plays").fetchone()[0] == 3
        # most recent name wins
        assert conn.execute("SELECT name FROM artists WHERE id='a1'").fetchone()[0] == "New Name"
        assert conn.execute("SELECT COUNT(*) FROM artists").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM albums").fetchone()[0] == 1  # NULL album skipped
        assert conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM track_artists").fetchone()[0] == 2
        # nothing is marked enriched; the API backfill still has to run
        assert conn.execute(
            "SELECT COUNT(*) FROM artists WHERE enriched_at IS NOT NULL").fetchone()[0] == 0
        assert [v for (v,) in conn.execute("SELECT version FROM schema_migrations")] == [1, 2]
        cols = [r[1] for r in conn.execute("PRAGMA table_info(plays)")]
        assert "context_type" in cols


def test_v2_is_applied_once_and_rerun_is_a_noop(tmp_path):
    path = tmp_path / "plays.db"
    _v1_database_with_plays(path)
    migrate(db_path=path)
    migrate(db_path=path)  # would fail on ALTER TABLE if V2 re-ran
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM artists").fetchone()[0] == 2
