"""Thin layer over the Spotify Web API calls we use. Everything returned is a plain
dict shaped for our tables, so the rest of the code never touches raw responses."""


def _largest_image(images):
    # Spotify lists images widest first
    return images[0]["url"] if images else None


def get_recently_played(sp, limit=50, after=None):
    """Recently played plays, newest first.

    `after` is a unix timestamp in ms. Spotify returns the *oldest* `limit` plays after
    the cursor (still ordered newest first), so a cursor never skips unseen plays.
    """
    kwargs = {"limit": limit}
    if after is not None:
        kwargs["after"] = after
    items = sp.current_user_recently_played(**kwargs)["items"]

    plays = []
    for item in items:
        track = item["track"]
        album = track["album"]
        context = item.get("context")
        plays.append({
            # raw ISO-8601 UTC string (e.g. 2025-08-19T20:57:21.365Z); this is the
            # format stored in the DB and compared as text by the email job
            "played_at": item["played_at"],
            "context_uri": context["uri"] if context else None,
            "context_type": context["type"] if context else None,
            "track": {
                "id": track["id"],
                "name": track["name"],
                "duration_ms": track.get("duration_ms"),
                "explicit": track.get("explicit"),
                "track_number": track.get("track_number"),
                "disc_number": track.get("disc_number"),
                "isrc": (track.get("external_ids") or {}).get("isrc"),
            },
            "album": {
                "id": album["id"],
                "name": album["name"],
                "album_type": album.get("album_type"),
                "release_date": album.get("release_date"),
                "release_date_precision": album.get("release_date_precision"),
                "total_tracks": album.get("total_tracks"),
                "image_url": _largest_image(album.get("images", [])),
            },
            "artists": [{"id": a["id"], "name": a["name"]} for a in track["artists"]],
        })
    return plays


def get_artist(sp, artist_id):
    a = sp.artist(artist_id)
    return {
        "id": a["id"],
        "name": a["name"],
        "genres": a.get("genres") or [],
        "image_url": _largest_image(a.get("images", [])),
        # deprecated by Spotify; present today but may disappear
        "popularity": a.get("popularity"),
        "followers_total": (a.get("followers") or {}).get("total"),
    }


def get_album(sp, album_id):
    a = sp.album(album_id)
    return {
        "id": a["id"],
        "name": a["name"],
        "album_type": a.get("album_type"),
        "release_date": a.get("release_date"),
        "release_date_precision": a.get("release_date_precision"),
        "total_tracks": a.get("total_tracks"),
        "image_url": _largest_image(a.get("images", [])),
    }
