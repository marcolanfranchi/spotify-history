from auth import get_spotify_client
from datetime import datetime

sp = get_spotify_client()

def get_my_profile():
    profile = sp.current_user()
    return {
        "id": profile["id"],
        "display_name": profile.get("display_name")
    }

def get_recently_played(limit=50):
    results = sp.current_user_recently_played(limit=limit)
    tracks = []
    for item in results["items"]:
        track = item["track"]
        album = track["album"]
        artist = track["artists"][0]  # main artist only
        context = item.get("context")
        tracks.append({
            "played_at": datetime.strptime(item["played_at"], "%Y-%m-%dT%H:%M:%S.%fZ"),
            "track": {
                "id": track["id"],
                "name": track["name"],
                "duration_ms": track.get("duration_ms"),
                "artist": {"id": artist["id"], "name": artist["name"]},
                "album": {"id": album["id"], "name": album["name"]}
            },
            "context": {
                "type": context["type"] if context else None,
                "uri": context["uri"] if context else None
            } if context else None
        })
    return tracks
