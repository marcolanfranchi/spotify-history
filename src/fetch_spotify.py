from inserter import upsert_user, insert_play
from auth import get_spotify_client

def run():
    sp = get_spotify_client()

    # 1️⃣ Upsert user
    me = sp.current_user()
    user_db_id = upsert_user(me['id'], me.get('display_name'))

    # 2️⃣ Fetch recently played tracks
    recent_tracks = sp.current_user_recently_played(limit=50)['items']

    for item in recent_tracks:
        track_info = item['track']
        artist = track_info['artists'][0]  # main artist only
        album_info = track_info['album']
        context = item.get('context')
        played_at = item['played_at']

        insert_play(
            user_db_id=user_db_id,
            track_id=track_info['id'],
            track_name=track_info['name'],
            artist_id=artist['id'],
            artist_name=artist['name'],
            album_id=album_info['id'],
            album_name=album_info['name'],
            played_at=played_at,
            duration_ms=track_info.get('duration_ms'),
            context_uri=context['uri'] if context else None,
        )

if __name__ == "__main__":
    run()
