#!/bin/bash
CRON_SCHEDULE="0 * * * *"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_PATH="$PROJECT_DIR/src/export_and_push.sh"
LOG_PATH="$PROJECT_DIR/spotify.log"

# Remove existing cron entry, then add a new one
(crontab -l 2>/dev/null | grep -Fv "$SCRIPT_PATH"; \
 echo "$CRON_SCHEDULE bash $SCRIPT_PATH >> $LOG_PATH 2>&1") | crontab -

echo "Export + push cron job installed: $CRON_SCHEDULE"

