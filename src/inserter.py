from db import get_conn

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
                album_id, album_name, played_at, duration_ms, context_uri):
    sql = """
    INSERT OR IGNORE INTO plays 
    (user_id, track_id, track_name, artist_id, artist_name, album_id, album_name, 
     played_at, duration_ms, context_uri)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, (
            user_db_id, track_id, track_name, artist_id, artist_name,
            album_id, album_name, played_at, duration_ms, context_uri
        ))

