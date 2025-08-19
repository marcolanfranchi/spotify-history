#!/bin/bash
# Schedule: every 10 minutes
CRON_SCHEDULE="*/10 * * * *"
CRON_LOG="$(pwd)/spotify.log"
PYTHON_FILE="$(pwd)/src/fetch_spotify.py"

# Remove any existing cron job for this script, then add new
(crontab -l 2>/dev/null | grep -Fv "$PYTHON_FILE"; echo "$CRON_SCHEDULE python3 $PYTHON_FILE >> $CRON_LOG 2>&1") | crontab -

echo "Fetch Spotify cron job installed: $CRON_SCHEDULE"
