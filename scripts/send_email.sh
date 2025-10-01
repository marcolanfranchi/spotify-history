#!/bin/bash
# Schedule: daily 12:01am 
CRON_SCHEDULE="01 0 * * *"
CRON_LOG="$(pwd)/spotify.log"
PYTHON_FILE="$(pwd)/src/send_email.py"
VENV_PYTHON="$(pwd)/venv/bin/python3"

# Remove any existing cron job for this script, then add new
(crontab -l 2>/dev/null | grep -Fv "$PYTHON_FILE"; echo "$CRON_SCHEDULE $VENV_PYTHON $PYTHON_FILE >> $CRON_LOG 2>&1") | crontab -

echo "Send Email cron job installed: $CRON_SCHEDULE"

