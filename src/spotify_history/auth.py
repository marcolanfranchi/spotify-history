import spotipy
from spotipy.oauth2 import SpotifyOAuth

from spotify_history import config


def get_spotify_client(**spotify_kwargs):
    """Authenticated client; kwargs go to spotipy.Spotify (e.g. retries, requests_timeout)."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    sp_oauth = SpotifyOAuth(
        client_id=config.SPOTIFY_CLIENT_ID,
        client_secret=config.SPOTIFY_CLIENT_SECRET,
        redirect_uri=config.SPOTIFY_REDIRECT_URI,
        scope=config.SPOTIFY_SCOPE,
        cache_path=str(config.TOKEN_PATH),
    )

    token_info = sp_oauth.get_cached_token()
    if not token_info:
        # first-time auth (needs to be done manually, not from cron)
        auth_url = sp_oauth.get_authorize_url()
        print(f"Visit this URL to authorize: {auth_url}")
        response = input("Paste the URL you were redirected to: ")
        code = sp_oauth.parse_response_code(response)
        token_info = sp_oauth.get_access_token(code, as_dict=True)

    # always refresh if needed
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])

    return spotipy.Spotify(auth=token_info["access_token"], **spotify_kwargs)
