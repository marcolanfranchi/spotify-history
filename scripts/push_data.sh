#!/bin/bash

CRON_SCHEDULE="5 0,12 * * *"
PROJECT_DIR="$(pwd)"
SCRIPT_PATH="$PROJECT_DIR/scripts/export_and_push_plays.sh"
LOG_PATH="$PROJECT_DIR/spotif.log"

# Remove any existing cron job for this script, then add new
(crontab -l 2>/dev/null | grep -Fv "$SCRIPT_PATH"; echo "$CRON_SCHEDULE bash $SCRIPT_PATH >> $LOG_PATH 2>&1") | crontab -

echo "Export + push cron job installed: $CRON_SCHEDULE"
