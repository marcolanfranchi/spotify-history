from spotify_history.client import get_recently_played
from spotify_history.db.connection import get_conn
from spotify_history.db.repository import get_latest_played_at_ms, record_plays, upsert_user
from spotify_history.jobs import fetch
from tests.fakes import FakeSpotify, api_play


def _rows(sql, *params):
    with get_conn() as conn:
        return [tuple(r) for r in conn.execute(sql, params).fetchall()]


def test_client_normalizes_play():
    sp = FakeSpotify([api_play("2025-08-19T20:57:21.365Z", artists=(("a1", "A"), ("a2", "B")))])
    (play,) = get_recently_played(sp)
    assert play["played_at"] == "2025-08-19T20:57:21.365Z"  # raw string preserved
    assert play["context_type"] == "playlist"
    assert [a["id"] for a in play["artists"]] == ["a1", "a2"]
    assert play["track"]["isrc"] == "ISRCt1"
    assert play["album"]["image_url"] == "http://img/al1/big"  # widest first


def test_client_handles_missing_context():
    sp = FakeSpotify([api_play("2025-08-19T20:57:21.365Z", context=None)])
    (play,) = get_recently_played(sp)
    assert play["context_uri"] is None and play["context_type"] is None


def test_client_only_sends_after_when_given():
    sp = FakeSpotify([])
    get_recently_played(sp, limit=50)
    get_recently_played(sp, limit=50, after=123)
    assert sp.calls == [("recently_played", 50, None), ("recently_played", 50, 123)]


def test_record_plays_writes_all_tables(db):
    user = upsert_user("spotify-user")
    sp = FakeSpotify([api_play("2025-08-19T20:57:21.365Z", artists=(("a1", "A"), ("a2", "B")))])

    assert record_plays(user, get_recently_played(sp)) == 1

    # denormalized play row keeps first artist and gets the context type
    assert _rows("SELECT artist_id, artist_name, context_type, context_uri FROM plays") == [
        ("a1", "A", "playlist", "spotify:playlist:p1")
    ]
    assert _rows("SELECT id FROM artists ORDER BY id") == [("a1",), ("a2",)]
    assert _rows("SELECT artist_id, position FROM track_artists ORDER BY position") == [
        ("a1", 0), ("a2", 1)
    ]
    assert _rows("SELECT explicit, track_number, isrc FROM tracks") == [(0, 3, "ISRCt1")]
    assert _rows("SELECT album_type, release_date, enriched_at IS NOT NULL FROM albums") == [
        ("album", "2024-05-01", 1)
    ]


def test_record_plays_is_idempotent(db):
    user = upsert_user("spotify-user")
    plays = get_recently_played(FakeSpotify([api_play("2025-08-19T20:57:21.365Z")]))
    assert record_plays(user, plays) == 1
    assert record_plays(user, plays) == 0
    assert _rows("SELECT COUNT(*) FROM plays") == [(1,)]
    assert _rows("SELECT COUNT(*) FROM track_artists") == [(1,)]


def test_reseen_artist_keeps_enrichment(db):
    user = upsert_user("spotify-user")
    record_plays(user, get_recently_played(FakeSpotify([api_play("2025-08-19T20:57:21.365Z")])))
    with get_conn() as conn:
        conn.execute("UPDATE artists SET enriched_at = '2026-01-01', image_url = 'x' WHERE id='a1'")
        conn.execute("INSERT INTO artist_genres VALUES ('a1', 'shoegaze')")

    record_plays(user, get_recently_played(FakeSpotify([api_play("2025-08-19T21:00:00.000Z")])))

    assert _rows("SELECT enriched_at, image_url FROM artists WHERE id='a1'") == [("2026-01-01", "x")]
    assert _rows("SELECT genre FROM artist_genres") == [("shoegaze",)]


def test_latest_played_at_ms(db):
    user = upsert_user("spotify-user")
    assert get_latest_played_at_ms(user) is None
    record_plays(user, get_recently_played(FakeSpotify([
        api_play("2025-08-19T20:57:21.365Z", track_id="t1"),
        api_play("2025-08-19T20:00:00.000Z", track_id="t2"),
    ])))
    assert get_latest_played_at_ms(user) == 1755637041365


def test_fetch_uses_after_cursor_and_reports_new(db, capsys):
    sp = FakeSpotify([api_play("2025-08-19T20:57:21.365Z")])
    assert fetch.run(sp=sp) == 1
    assert sp.calls[-1] == ("recently_played", 50, None)  # first run: no cursor

    assert fetch.run(sp=sp) == 0
    assert sp.calls[-1] == ("recently_played", 50, 1755637041365)
    assert "WARNING" not in capsys.readouterr().out


def test_fetch_warns_when_response_is_full(db, capsys):
    first = FakeSpotify([api_play("2025-08-19T20:00:00.000Z", track_id="old")])
    fetch.run(sp=first)
    full = FakeSpotify([
        api_play(f"2025-08-20T{h:02d}:{m:02d}:00.000Z", track_id=f"t{h}-{m}")
        for h in range(5) for m in range(10)
    ])
    fetch.run(sp=full)
    assert "WARNING" in capsys.readouterr().out

