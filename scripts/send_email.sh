#!/bin/bash
# Schedule: daily 12:02am
CRON_SCHEDULE="2 0 * * *"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_PATH="$PROJECT_DIR/data/spotify.log"

# Use the project's .venv (or venv); override with PYTHON=/path/to/python3
PYTHON="${PYTHON:-$PROJECT_DIR/.venv/bin/python3}"
[ -x "$PYTHON" ] || PYTHON="$PROJECT_DIR/venv/bin/python3"
mkdir -p "$PROJECT_DIR/data"

# Remove any existing cron job for this script, then add new
(crontab -l 2>/dev/null | grep -Fv "# spotify-history:email"; \
 echo "$CRON_SCHEDULE cd $PROJECT_DIR && $PYTHON -m spotify_history email >> $LOG_PATH 2>&1 # spotify-history:email") | crontab -

echo "Send Email cron job installed: $CRON_SCHEDULE"
