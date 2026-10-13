"""Fill in artist (genres, images) and album details from the Spotify API.

Works through a queue of rows with enriched_at IS NULL, most-played first. Every run
is bounded by --limit API calls, throttled, and safe to stop and re-run, so the
historical backfill can be done in small batches over several days.
"""
import time

from spotipy.exceptions import SpotifyException

from spotify_history.auth import get_spotify_client
from spotify_history.client import get_album, get_artist
from spotify_history.db import enrichment

FETCHERS = {"artists": get_artist, "albums": get_album}
SAVERS = {"artists": enrichment.save_artist, "albums": enrichment.save_album}


def _enrich(sp, entity, budget, delay):
    """Returns (done, not_found, rate_limited) for one entity type."""
    done = not_found = 0
    for entity_id in enrichment.get_pending_ids(entity, budget):
        try:
            data = FETCHERS[entity](sp, entity_id)
        except SpotifyException as e:
            if e.http_status == 404:
                enrichment.mark_enriched_without_data(entity, entity_id)
                not_found += 1
                continue
            if e.http_status == 429:
                return done, not_found, True
            raise
        SAVERS[entity](data)
        done += 1
        if delay:
            time.sleep(delay)
    return done, not_found, False


def run(limit=50, only=None, delay=0.25, sp=None):
    """Make up to `limit` API calls (artists first, then albums). Returns exit code."""
    entities = [only] if only else ["artists", "albums"]
    sp = sp or get_spotify_client(retries=0, requests_timeout=15)

    remaining_budget = limit
    for entity in entities:
        if remaining_budget <= 0:
            break
        done, not_found, rate_limited = _enrich(sp, entity, remaining_budget, delay)
        remaining_budget -= done + not_found
        print(f"{entity}: enriched {done}, not found {not_found}")
        if rate_limited:
            print("Rate limited by Spotify (429); stopping. Re-run later to continue.")
            break

    for entity in ("artists", "albums"):
        print(f"{entity} still pending: {enrichment.count_pending(entity)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
