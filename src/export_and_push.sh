#!/bin/bash
# Exports plays.csv from SQLite and uploads to S3.
# If S3_BUCKET is not set, exits after saving data/plays.csv (not tracked by git).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

DB_PATH="$PROJECT_DIR/db/plays.db"
CSV_PATH="$PROJECT_DIR/data/plays.csv"
LOG_PATH="$PROJECT_DIR/spotify.log"
ENV_PATH="$PROJECT_DIR/.env"

# Ensure output goes to single log file
exec >> "$LOG_PATH" 2>&1

# Load .env for cron access
if [ -f "$ENV_PATH" ]; then
    set -o allexport
    source "$ENV_PATH"
    set +o allexport
fi

# Export from SQLite to CSV
sqlite3 -header -csv "$DB_PATH" \
"SELECT played_at, track_id, track_name, artist_name FROM plays WHERE user_id = 1 ORDER BY played_at DESC;" \
> "$CSV_PATH"

# Check if S3_BUCKET is set, if not exit
if [ -z "$S3_BUCKET" ]; then
    echo "S3_BUCKET not set — skipping S3 export"
    exit 0
fi

# Upload to S3
S3_KEY="$S3_PREFIX/plays.csv"
if aws s3 cp "$CSV_PATH" "s3://$S3_BUCKET/$S3_KEY" --region "$AWS_REGION"; then
    echo "S3 upload succeeded: s3://$S3_BUCKET/$S3_KEY at $(date)"
else
    echo "S3 upload failed at $(date)"
fi
