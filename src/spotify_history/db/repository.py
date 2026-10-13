from datetime import datetime

from spotify_history.db.connection import get_conn


def upsert_user(spotify_user_id, display_name=None):
    sql = """
    INSERT INTO users (spotify_user_id, display_name)
    VALUES (?, ?)
    ON CONFLICT(spotify_user_id) DO UPDATE SET display_name=excluded.display_name
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, (spotify_user_id, display_name))
        cur.execute("SELECT id FROM users WHERE spotify_user_id=?", (spotify_user_id,))
        return cur.fetchone()[0]


def insert_play(user_db_id, track_id, track_name, artist_id, artist_name,
                album_id, album_name, played_at, duration_ms, context_uri,
                context_type=None):
    """Insert a bare play row; duplicates (same user, track, played_at) are ignored."""
    with get_conn() as conn:
        return _insert_play_row(
            conn, user_db_id, track_id, track_name, artist_id, artist_name,
            album_id, album_name, played_at, duration_ms, context_uri, context_type,
        )


def _insert_play_row(conn, user_db_id, track_id, track_name, artist_id, artist_name,
                     album_id, album_name, played_at, duration_ms, context_uri,
                     context_type):
    cur = conn.execute(
        """
        INSERT OR IGNORE INTO plays
        (user_id, track_id, track_name, artist_id, artist_name, album_id, album_name,
         played_at, duration_ms, context_uri, context_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_db_id, track_id, track_name, artist_id, artist_name, album_id,
         album_name, played_at, duration_ms, context_uri, context_type),
    )
    return cur.rowcount


def record_plays(user_db_id, plays):
    """Store normalized plays (see client.get_recently_played) in one transaction.

    Writes the denormalized `plays` row plus artist / album / track / track_artists
    rows. Returns the number of plays that were new. Existing enrichment (genres,
    images, ...) is never overwritten by a re-seen artist.
    """
    new_plays = 0
    with get_conn() as conn:
        for play in plays:
            track, album, artists = play["track"], play["album"], play["artists"]
            main = artists[0]

            for artist in artists:
                conn.execute(
                    """
                    INSERT INTO artists (id, name) VALUES (?, ?)
                    ON CONFLICT(id) DO UPDATE SET name=excluded.name
                    """,
                    (artist["id"], artist["name"]),
                )

            # recently-played carries the same album fields as GET /albums/{id},
            # so an album seen here counts as enriched.
            conn.execute(
                """
                INSERT INTO albums (id, name, album_type, release_date,
                                    release_date_precision, total_tracks, image_url,
                                    enriched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    album_type=excluded.album_type,
                    release_date=excluded.release_date,
                    release_date_precision=excluded.release_date_precision,
                    total_tracks=excluded.total_tracks,
                    image_url=COALESCE(excluded.image_url, albums.image_url),
                    enriched_at=COALESCE(albums.enriched_at, excluded.enriched_at)
                """,
                (album["id"], album["name"], album["album_type"], album["release_date"],
                 album["release_date_precision"], album["total_tracks"],
                 album["image_url"]),
            )

            conn.execute(
                """
                INSERT INTO tracks (id, name, album_id, duration_ms, explicit,
                                    track_number, disc_number, isrc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    album_id=excluded.album_id,
                    duration_ms=excluded.duration_ms,
                    explicit=excluded.explicit,
                    track_number=excluded.track_number,
                    disc_number=excluded.disc_number,
                    isrc=COALESCE(excluded.isrc, tracks.isrc)
                """,
                (track["id"], track["name"], album["id"], track["duration_ms"],
                 None if track["explicit"] is None else int(track["explicit"]),
                 track["track_number"], track["disc_number"], track["isrc"]),
            )

            for position, artist in enumerate(artists):
                conn.execute(
                    """
                    INSERT INTO track_artists (track_id, artist_id, position)
                    VALUES (?, ?, ?)
                    ON CONFLICT(track_id, artist_id) DO UPDATE SET position=excluded.position
                    """,
                    (track["id"], artist["id"], position),
                )

            new_plays += _insert_play_row(
                conn, user_db_id, track["id"], track["name"], main["id"], main["name"],
                album["id"], album["name"], play["played_at"], track["duration_ms"],
                play["context_uri"], play["context_type"],
            )
    return new_plays


def get_latest_played_at_ms(user_db_id):
    """Unix ms of the newest stored play for the user, or None if there are none."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(played_at) FROM plays WHERE user_id = ?", (user_db_id,)
        ).fetchone()
    if not row or row[0] is None:
        return None
    parsed = datetime.strptime(row[0], "%Y-%m-%dT%H:%M:%S.%f%z")
    return int(parsed.timestamp() * 1000)


def get_plays_between(start_str, end_str):
    """Plays with start_str <= played_at < end_str (ISO-8601 UTC strings), oldest first."""
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT played_at, track_name, album_name, artist_name
            FROM plays
            WHERE played_at >= ? AND played_at < ?
            ORDER BY played_at ASC;
            """,
            (start_str, end_str),
        ).fetchall()
