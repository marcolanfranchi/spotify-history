from spotify_history.db.connection import get_conn
from spotify_history.db.repository import get_plays_between, insert_play, upsert_user

PLAY = dict(
    track_id="t1", track_name="Song", artist_id="a1", artist_name="Artist",
    album_id="al1", album_name="Album", played_at="2025-08-19T20:57:21.365Z",
    duration_ms=1000, context_uri=None,
)


def test_upsert_user_returns_stable_id(db):
    first = upsert_user("spotify-user", "Name")
    second = upsert_user("spotify-user", "New Name")
    assert first == second


def test_duplicate_plays_are_ignored(db):
    user = upsert_user("spotify-user")
    insert_play(user_db_id=user, **PLAY)
    insert_play(user_db_id=user, **PLAY)
    with get_conn() as conn:
        assert conn.execute("SELECT COUNT(*) FROM plays").fetchone()[0] == 1


def test_get_plays_between_is_half_open(db):
    user = upsert_user("spotify-user")
    insert_play(user_db_id=user, **PLAY)
    inside = get_plays_between("2025-08-19T20:00:00Z", "2025-08-19T21:00:00Z")
    outside = get_plays_between("2025-08-19T21:00:00Z", "2025-08-19T22:00:00Z")
    assert len(inside) == 1 and outside == []
