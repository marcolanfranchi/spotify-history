from spotify_history.auth import get_spotify_client
from spotify_history.client import get_recently_played
from spotify_history.db.repository import (
    get_latest_played_at_ms,
    record_plays,
    upsert_user,
)

LIMIT = 50


def run(sp=None):
    sp = sp or get_spotify_client()

    me = sp.current_user()
    user_db_id = upsert_user(me["id"], me.get("display_name"))

    after = get_latest_played_at_ms(user_db_id)
    plays = get_recently_played(sp, limit=LIMIT, after=after)
    new = record_plays(user_db_id, plays)

    print(f"Fetched {len(plays)} plays, {new} new")
    if after is not None and len(plays) >= LIMIT:
        # Spotify only keeps the last 50 plays; a full response means older unseen
        # plays may already have aged out of the window.
        print("WARNING: response was full; some plays since the last fetch may be missing")
    return new


if __name__ == "__main__":
    run()
