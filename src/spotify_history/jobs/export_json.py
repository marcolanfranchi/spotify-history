"""Export the database tables as JSON files for static consumers (the personal site).

Files are written to config.API_DIR and, on upload, published under <S3_PREFIX>/v1/:

    manifest.json   schema version, generation time, row counts, enrichment progress
    plays.json      one object per play, ids only (names come from the other tables)
    tracks.json     tracks with artist_ids (ordered) and album_id
    artists.json    artists with genres embedded
    albums.json     albums

Relations are plain ids, so consumers join with a Map lookup. The existing
plays.csv is untouched; this is additive. Bump SCHEMA_VERSION (and the v1 path)
for breaking changes to the shape.
"""
import gzip
import json
from datetime import datetime, timezone

from spotify_history import config
from spotify_history.db.connection import get_conn

SCHEMA_VERSION = 1
# Upload order: data files first, manifest last, so a reader that sees a manifest
# always finds the files it lists.
TABLE_ORDER = ["artists", "albums", "tracks", "plays"]


def _grouped(conn, sql):
    grouped = {}
    for key, value in conn.execute(sql):
        grouped.setdefault(key, []).append(value)
    return grouped


def build_tables(conn):
    genres = _grouped(
        conn, "SELECT artist_id, genre FROM artist_genres ORDER BY artist_id, genre"
    )
    track_artists = _grouped(
        conn, "SELECT track_id, artist_id FROM track_artists ORDER BY track_id, position"
    )

    artists = [
        {
            "id": r["id"],
            "name": r["name"],
            "genres": genres.get(r["id"], []),
            # False means genres are simply not fetched yet, not "no genres"
            "genres_known": r["enriched_at"] is not None,
            "image_url": r["image_url"],
            "popularity": r["popularity"],
            "followers_total": r["followers_total"],
        }
        for r in conn.execute(
            "SELECT id, name, image_url, popularity, followers_total, enriched_at "
            "FROM artists ORDER BY id"
        )
    ]
    albums = [
        dict(r) for r in conn.execute(
            "SELECT id, name, album_type, release_date, release_date_precision, "
            "total_tracks, image_url FROM albums ORDER BY id"
        )
    ]
    tracks = [
        {
            "id": r["id"],
            "name": r["name"],
            "album_id": r["album_id"],
            "artist_ids": track_artists.get(r["id"], []),
            "duration_ms": r["duration_ms"],
            "explicit": None if r["explicit"] is None else bool(r["explicit"]),
            "track_number": r["track_number"],
            "disc_number": r["disc_number"],
            "isrc": r["isrc"],
        }
        for r in conn.execute(
            "SELECT id, name, album_id, duration_ms, explicit, track_number, "
            "disc_number, isrc FROM tracks ORDER BY id"
        )
    ]
    plays = [
        dict(r) for r in conn.execute(
            "SELECT played_at, track_id, artist_id, album_id, context_type "
            "FROM plays WHERE user_id = 1 ORDER BY played_at DESC"
        )
    ]
    return {"artists": artists, "albums": albums, "tracks": tracks, "plays": plays}


def build_manifest(tables, generated_at=None):
    generated_at = generated_at or datetime.now(timezone.utc)
    plays = tables["plays"]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tables": {name: {"file": f"{name}.json", "rows": len(tables[name])}
                   for name in TABLE_ORDER},
        "plays_range": {
            "first": plays[-1]["played_at"] if plays else None,
            "last": plays[0]["played_at"] if plays else None,
        },
        "enrichment": {
            "artists_total": len(tables["artists"]),
            "artists_with_genres_known": sum(a["genres_known"] for a in tables["artists"]),
        },
    }


def _dump(obj):
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def write_json_files(out_dir=None):
    """Write all tables plus the manifest as plain JSON; returns the manifest."""
    out_dir = out_dir or config.API_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        tables = build_tables(conn)
    manifest = build_manifest(tables)
    for name in TABLE_ORDER:
        (out_dir / f"{name}.json").write_text(_dump(tables[name]), encoding="utf-8")
    (out_dir / "manifest.json").write_text(_dump(manifest), encoding="utf-8")
    return manifest


def gzipped(path):
    # mtime=0 keeps the bytes stable when the content hasn't changed
    return gzip.compress(path.read_bytes(), mtime=0)
