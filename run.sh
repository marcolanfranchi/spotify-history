#!/bin/bash
# One-shot setup: create/upgrade the database, run a first fetch, install cron jobs.
# Uses the project's .venv (or venv); override with PYTHON=/path/to/python3.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [ -z "${PYTHON:-}" ]; then
    for venv in .venv venv; do
        [ -x "$PROJECT_DIR/$venv/bin/python3" ] && PYTHON="$PROJECT_DIR/$venv/bin/python3" && break
    done
fi
export PYTHON="${PYTHON:-$PROJECT_DIR/.venv/bin/python3}"

echo "Initializing database..."
"$PYTHON" -m spotify_history migrate

echo "Fetching last 50 plays to start (authorizes Spotify on first run)..."
"$PYTHON" -m spotify_history fetch

echo "Installing cron jobs..."
bash scripts/fetch_spotify.sh
bash scripts/send_email.sh
bash scripts/push_data.sh

echo "All done!"
echo "Your Spotify plays will be updated in the SQLite db every 10 minutes."
echo "You will receive a daily email summary at 12:02am."
echo "You can view logs at $PROJECT_DIR/data/spotify.log"
