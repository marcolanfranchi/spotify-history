from spotify_history.client import get_recently_played
from spotify_history.db.connection import get_conn
from spotify_history.db.repository import record_plays, upsert_user
from spotify_history.jobs import enrich
from tests.fakes import FakeSpotify, api_album, api_artist, api_play


def _seed_plays(entries):
    """entries: list of (played_at, track_id, artist_id, album_id)"""
    user = upsert_user("spotify-user")
    sp = FakeSpotify([
        api_play(at, track_id=t, artists=((a, f"Artist {a}"),), album_id=al)
        for at, t, a, al in entries
    ])
    record_plays(user, get_recently_played(sp))
    # simulate not-yet-enriched albums (as after the V2 stub backfill of old plays)
    with get_conn() as conn:
        conn.execute("UPDATE albums SET enriched_at = NULL")


def _scalar(sql, *params):
    with get_conn() as conn:
        return conn.execute(sql, params).fetchone()[0]


def _entries():
    # artist a1: 3 plays, a2: 2 plays, a3: 1 play
    return [
        ("2025-01-01T00:00:0%d.000Z" % i, f"t{i}", a, f"al-{a}")
        for i, a in enumerate(["a1", "a1", "a1", "a2", "a2", "a3"])
    ]


def _api():
    return dict(
        artists={i: api_artist(i, genres=("g-" + i, "common")) for i in ("a1", "a2", "a3")},
        albums={f"al-{i}": api_album(f"al-{i}") for i in ("a1", "a2", "a3")},
    )


def test_enrich_saves_genres_and_details(db):
    _seed_plays(_entries())
    sp = FakeSpotify(**_api())

    assert enrich.run(limit=100, delay=0, sp=sp) == 0

    assert _scalar("SELECT COUNT(*) FROM artists WHERE enriched_at IS NULL") == 0
    assert _scalar("SELECT COUNT(*) FROM albums WHERE enriched_at IS NULL") == 0
    with get_conn() as conn:
        genres = sorted(r[0] for r in conn.execute(
            "SELECT genre FROM artist_genres WHERE artist_id='a1'"))
        row = conn.execute("SELECT image_url, popularity, followers_total FROM artists "
                           "WHERE id='a1'").fetchone()
    assert genres == ["common", "g-a1"]
    assert tuple(row) == ("http://img/a1", 42, 1000)
    assert _scalar("SELECT release_date FROM albums WHERE id='al-a1'") == "2020"


def test_limit_bounds_api_calls_and_runs_resume(db):
    _seed_plays(_entries())
    sp = FakeSpotify(**_api())

    enrich.run(limit=2, delay=0, sp=sp)
    assert len(sp.calls) == 2
    assert _scalar("SELECT COUNT(*) FROM artists WHERE enriched_at IS NOT NULL") == 2

    enrich.run(limit=2, delay=0, sp=sp)  # artists done after 1 more, then 1 album
    assert _scalar("SELECT COUNT(*) FROM artists WHERE enriched_at IS NULL") == 0
    assert len(sp.calls) == 4
    assert _scalar("SELECT COUNT(*) FROM albums WHERE enriched_at IS NOT NULL") == 1


def test_most_played_artists_are_enriched_first(db):
    _seed_plays(_entries())
    sp = FakeSpotify(**_api())
    enrich.run(limit=2, only="artists", delay=0, sp=sp)
    assert [c[1] for c in sp.calls] == ["a1", "a2"]


def test_only_albums_skips_artists(db):
    _seed_plays(_entries())
    sp = FakeSpotify(**_api())
    enrich.run(limit=100, only="albums", delay=0, sp=sp)
    assert {c[0] for c in sp.calls} == {"album"}
    assert _scalar("SELECT COUNT(*) FROM artists WHERE enriched_at IS NULL") == 3


def test_not_found_is_marked_and_not_retried(db):
    _seed_plays(_entries())
    sp = FakeSpotify(errors={"a3": 404}, **_api())
    enrich.run(limit=100, only="artists", delay=0, sp=sp)
    assert _scalar("SELECT COUNT(*) FROM artists WHERE enriched_at IS NULL") == 0
    assert _scalar("SELECT COUNT(*) FROM artist_genres WHERE artist_id='a3'") == 0

    sp.calls.clear()
    enrich.run(limit=100, only="artists", delay=0, sp=sp)
    assert sp.calls == []


def test_rate_limit_stops_run_and_keeps_progress(db, capsys):
    _seed_plays(_entries())
    sp = FakeSpotify(errors={"a2": 429}, **_api())

    assert enrich.run(limit=100, delay=0, sp=sp) == 0

    out = capsys.readouterr().out
    assert "Rate limited" in out
    assert _scalar("SELECT enriched_at IS NOT NULL FROM artists WHERE id='a1'") == 1
    assert _scalar("SELECT enriched_at IS NULL FROM artists WHERE id='a2'") == 1
    assert ("album", "al-a1") not in sp.calls  # stopped before albums


def test_albums_seen_via_fetch_are_not_requeued(db):
    user = upsert_user("spotify-user")
    record_plays(user, get_recently_played(FakeSpotify([api_play("2025-01-01T00:00:00.000Z")])))
    sp = FakeSpotify(**_api())
    enrich.run(limit=100, only="albums", delay=0, sp=sp)
    assert sp.calls == []
