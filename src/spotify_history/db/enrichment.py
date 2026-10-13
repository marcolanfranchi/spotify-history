"""Queue and write helpers for filling in artist / album details from the API."""
from spotify_history.db.connection import get_conn


def count_pending(entity):
    table = _table(entity)
    with get_conn() as conn:
        return conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE enriched_at IS NULL"
        ).fetchone()[0]


def get_pending_ids(entity, limit):
    """Ids still needing enrichment, most-played first so the best data lands first."""
    table = _table(entity)
    play_col = "artist_id" if entity == "artists" else "album_id"
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT t.id
            FROM {table} t
            LEFT JOIN plays p ON p.{play_col} = t.id
            WHERE t.enriched_at IS NULL
            GROUP BY t.id
            ORDER BY COUNT(p.id) DESC, t.id
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [r[0] for r in rows]


def save_artist(artist):
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE artists
            SET name = ?, image_url = ?, popularity = ?, followers_total = ?,
                enriched_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (artist["name"], artist["image_url"], artist["popularity"],
             artist["followers_total"], artist["id"]),
        )
        conn.execute("DELETE FROM artist_genres WHERE artist_id = ?", (artist["id"],))
        conn.executemany(
            "INSERT OR IGNORE INTO artist_genres (artist_id, genre) VALUES (?, ?)",
            [(artist["id"], g) for g in artist["genres"]],
        )


def save_album(album):
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE albums
            SET name = ?, album_type = ?, release_date = ?, release_date_precision = ?,
                total_tracks = ?, image_url = ?, enriched_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (album["name"], album["album_type"], album["release_date"],
             album["release_date_precision"], album["total_tracks"],
             album["image_url"], album["id"]),
        )


def mark_enriched_without_data(entity, entity_id):
    """For ids Spotify no longer knows (404): stop retrying them forever."""
    table = _table(entity)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE {table} SET enriched_at = CURRENT_TIMESTAMP WHERE id = ?",
            (entity_id,),
        )


def _table(entity):
    if entity not in ("artists", "albums"):
        raise ValueError(f"unknown entity: {entity}")
    return entity
