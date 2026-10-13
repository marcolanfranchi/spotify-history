"""A minimal in-memory stand-in for spotipy.Spotify (no network)."""
from spotipy.exceptions import SpotifyException


def api_play(played_at, track_id="t1", artists=(("a1", "Artist One"),), album_id="al1",
             context=("playlist", "spotify:playlist:p1"), explicit=False):
    return {
        "played_at": played_at,
        "context": {"type": context[0], "uri": context[1]} if context else None,
        "track": {
            "id": track_id,
            "name": f"Track {track_id}",
            "duration_ms": 180000,
            "explicit": explicit,
            "track_number": 3,
            "disc_number": 1,
            "external_ids": {"isrc": f"ISRC{track_id}"},
            "artists": [{"id": i, "name": n} for i, n in artists],
            "album": {
                "id": album_id,
                "name": f"Album {album_id}",
                "album_type": "album",
                "release_date": "2024-05-01",
                "release_date_precision": "day",
                "total_tracks": 10,
                "images": [{"url": f"http://img/{album_id}/big"}, {"url": "http://img/small"}],
            },
        },
    }


class FakeSpotify:
    def __init__(self, plays=(), artists=None, albums=None, errors=None):
        self.plays = list(plays)
        self.artists = artists or {}
        self.albums = albums or {}
        self.errors = errors or {}  # id -> http status to raise
        self.calls = []

    def current_user(self):
        return {"id": "spotify-user", "display_name": "Me"}

    def current_user_recently_played(self, limit=20, after=None):
        self.calls.append(("recently_played", limit, after))
        return {"items": self.plays[:limit]}

    def _maybe_fail(self, entity_id):
        status = self.errors.get(entity_id)
        if status:
            raise SpotifyException(status, -1, f"error {status}")

    def artist(self, artist_id):
        self.calls.append(("artist", artist_id))
        self._maybe_fail(artist_id)
        return self.artists[artist_id]

    def album(self, album_id):
        self.calls.append(("album", album_id))
        self._maybe_fail(album_id)
        return self.albums[album_id]


def api_artist(artist_id, genres=("indie rock",), popularity=42, followers=1000):
    return {
        "id": artist_id,
        "name": f"Artist {artist_id}",
        "genres": list(genres),
        "images": [{"url": f"http://img/{artist_id}"}],
        "popularity": popularity,
        "followers": {"total": followers},
    }


def api_album(album_id):
    return {
        "id": album_id,
        "name": f"Album {album_id}",
        "album_type": "single",
        "release_date": "2020",
        "release_date_precision": "year",
        "total_tracks": 1,
        "images": [{"url": f"http://img/{album_id}"}],
    }
