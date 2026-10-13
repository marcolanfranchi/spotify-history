import gzip
import json

from spotify_history import config
from spotify_history.client import get_recently_played
from spotify_history.db.connection import get_conn
from spotify_history.db.repository import record_plays, upsert_user
from spotify_history.jobs import export, export_json
from tests.fakes import FakeSpotify, api_play


def _seed_rich(db):
    user = upsert_user("spotify-user")
    sp = FakeSpotify([
        api_play("2025-08-19T21:00:00.000Z", track_id="t2", artists=(("a1", "A"), ("a2", "B")),
                 album_id="al1"),
        api_play("2025-08-19T20:00:00.000Z", track_id="t1", artists=(("a1", "A"),),
                 album_id="al1", context=None),
    ])
    record_plays(user, get_recently_played(sp))
    with get_conn() as conn:  # a1 enriched with genres, a2 not yet
        conn.execute("UPDATE artists SET enriched_at='2026-01-01' WHERE id='a1'")
        conn.executemany("INSERT INTO artist_genres VALUES ('a1', ?)",
                         [("shoegaze",), ("emo",)])


def _read(name):
    return json.loads((config.API_DIR / f"{name}.json").read_text(encoding="utf-8"))


def test_writes_all_tables_and_manifest(db):
    _seed_rich(db)
    manifest = export_json.write_json_files()

    assert {p.name for p in config.API_DIR.iterdir()} == {
        "artists.json", "albums.json", "tracks.json", "plays.json", "manifest.json"}
    assert manifest == _read("manifest")
    assert manifest["schema_version"] == 1
    assert manifest["tables"]["plays"] == {"file": "plays.json", "rows": 2}
    assert manifest["plays_range"] == {
        "first": "2025-08-19T20:00:00.000Z", "last": "2025-08-19T21:00:00.000Z"}
    assert manifest["enrichment"] == {"artists_total": 2, "artists_with_genres_known": 1}


def test_plays_are_newest_first_and_ids_only(db):
    _seed_rich(db)
    export_json.write_json_files()
    plays = _read("plays")
    assert [p["track_id"] for p in plays] == ["t2", "t1"]
    assert set(plays[0]) == {"played_at", "track_id", "artist_id", "album_id", "context_type"}
    assert plays[0]["artist_id"] == "a1" and plays[0]["album_id"] == "al1"
    assert plays[0]["context_type"] == "playlist"
    assert plays[1]["context_type"] is None
    # names are reachable by joining, not duplicated per play
    names = {t["id"]: t["name"] for t in _read("tracks")}
    assert names[plays[0]["track_id"]] == "Track t2"


def test_genres_are_embedded_and_unknown_is_distinguished_from_empty(db):
    _seed_rich(db)
    export_json.write_json_files()
    artists = {a["id"]: a for a in _read("artists")}
    assert artists["a1"]["genres"] == ["emo", "shoegaze"] and artists["a1"]["genres_known"]
    assert artists["a2"]["genres"] == [] and artists["a2"]["genres_known"] is False


def test_tracks_keep_all_artists_in_order(db):
    _seed_rich(db)
    export_json.write_json_files()
    tracks = {t["id"]: t for t in _read("tracks")}
    assert tracks["t2"]["artist_ids"] == ["a1", "a2"]
    assert tracks["t1"]["artist_ids"] == ["a1"]
    assert tracks["t1"]["explicit"] is False


def test_every_reference_resolves_so_consumers_can_join(db):
    _seed_rich(db)
    export_json.write_json_files()
    artists = {a["id"] for a in _read("artists")}
    albums = {a["id"] for a in _read("albums")}
    tracks = {t["id"]: t for t in _read("tracks")}
    for p in _read("plays"):
        assert p["track_id"] in tracks and p["artist_id"] in artists and p["album_id"] in albums
    for t in tracks.values():
        assert t["album_id"] in albums and set(t["artist_ids"]) <= artists


def test_gzipped_bytes_round_trip(db):
    _seed_rich(db)
    export_json.write_json_files()
    path = config.API_DIR / "plays.json"
    assert gzip.decompress(export_json.gzipped(path)) == path.read_bytes()
    assert export_json.gzipped(path) == export_json.gzipped(path)  # deterministic


def test_csv_output_is_unchanged_by_json_export(db):
    _seed_rich(db)
    export.run()
    lines = config.CSV_PATH.read_text().splitlines()
    assert lines[0] == "played_at,track_id,track_name,artist_name"
    assert lines[1] == "2025-08-19T21:00:00.000Z,t2,Track t2,A"
