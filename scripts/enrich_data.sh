#!/bin/bash
# Schedule: hourly at :17. Fills in artist genres / album details for newly seen
# artists and albums (and slowly works through any backfill backlog).
# Not installed by run.sh; run this script if you want steady-state enrichment.
CRON_SCHEDULE="17 * * * *"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_PATH="$PROJECT_DIR/data/spotify.log"

# Use the project's .venv (or venv); override with PYTHON=/path/to/python3
PYTHON="${PYTHON:-$PROJECT_DIR/.venv/bin/python3}"
[ -x "$PYTHON" ] || PYTHON="$PROJECT_DIR/venv/bin/python3"
mkdir -p "$PROJECT_DIR/data"

# Remove any existing cron job for this script, then add new
(crontab -l 2>/dev/null | grep -Fv "# spotify-history:enrich"; \
 echo "$CRON_SCHEDULE cd $PROJECT_DIR && $PYTHON -m spotify_history enrich --limit 20 >> $LOG_PATH 2>&1 # spotify-history:enrich") | crontab -

echo "Enrich cron job installed: $CRON_SCHEDULE"
