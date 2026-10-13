#!/bin/bash
# Schedule: every 30 minutes (at :01 and :31); uploads to S3 only if S3_BUCKET is set
CRON_SCHEDULE="1,31 * * * *"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_PATH="$PROJECT_DIR/data/spotify.log"

# Use the project's .venv (or venv); override with PYTHON=/path/to/python3
PYTHON="${PYTHON:-$PROJECT_DIR/.venv/bin/python3}"
[ -x "$PYTHON" ] || PYTHON="$PROJECT_DIR/venv/bin/python3"
mkdir -p "$PROJECT_DIR/data"

# Remove any existing cron job for this script, then add new
(crontab -l 2>/dev/null | grep -Fv "# spotify-history:export"; \
 echo "$CRON_SCHEDULE cd $PROJECT_DIR && $PYTHON -m spotify_history export --upload >> $LOG_PATH 2>&1 # spotify-history:export") | crontab -

echo "S3 export cron job installed: $CRON_SCHEDULE"
