import os

import spotipy
from dotenv import load_dotenv
from spotipy.exceptions import SpotifyOauthError
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

# These env vars should be set in your .env file
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
SCOPE = "playlist-read-private user-library-read user-read-recently-played"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_PATH = os.path.join(PROJECT_ROOT, ".spotify_token")

sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope=SCOPE,
    cache_path=CACHE_PATH
)

def get_spotify_client():
    token_info = sp_oauth.get_cached_token()

    if token_info and sp_oauth.is_token_expired(token_info):
        try:
            token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        except SpotifyOauthError as e:
            # refresh token revoked/invalid - drop the stale cache and re-authorize
            print(f"Cached refresh token is no longer valid ({e}); clearing cache and re-authorizing.")
            if os.path.exists(CACHE_PATH):
                os.remove(CACHE_PATH)
            token_info = None

    if not token_info:
        # first-time (or forced re-) auth - needs to be run interactively.
        # The URL can be opened on ANY device (phone, laptop, etc.) - it does not
        # need to be the same machine this script is running on. After approving,
        # the browser will redirect to SPOTIFY_REDIRECT_URI and fail to load (expected) -
        # just copy the full URL from the address bar and paste it below.
        auth_url = sp_oauth.get_authorize_url()
        print(f"Visit this URL to authorize: {auth_url}")
        response = input("Paste the URL you were redirected to: ")
        code = sp_oauth.parse_response_code(response)
        token_info = sp_oauth.get_access_token(code, as_dict=True)

    return spotipy.Spotify(auth=token_info["access_token"])


if __name__ == "__main__":
    get_spotify_client()
    print("Spotify authentication successful - token cached at", CACHE_PATH)

