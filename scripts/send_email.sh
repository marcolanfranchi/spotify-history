#!/bin/bash
# Schedule: daily 7am UTC
CRON_SCHEDULE="0 7 * * *"
CRON_LOG="$(pwd)/spotify.log"
PYTHON_FILE="$(pwd)/src/send_email.py"

# Remove any existing cron job for this script, then add new
(crontab -l 2>/dev/null | grep -Fv "$PYTHON_FILE"; echo "$CRON_SCHEDULE python3 $PYTHON_FILE >> $CRON_LOG 2>&1") | crontab -

echo "Send Email cron job installed: $CRON_SCHEDULE"
