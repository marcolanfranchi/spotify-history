#!/bin/bash

# Paths (adjust these!)
PROJECT_DIR="$(pwd)"
DB_PATH="$PROJECT_DIR/db/plays.db"
CSV_PATH="$PROJECT_DIR/data/plays.csv"
LOG_PATH="$PROJECT_DIR/spotify_export.log"

# Git info
GIT_BRANCH="main"
COMMIT_MSG="Exported plays.csv on $(date '+%Y-%m-%d %H:%M:%S') (automated)"

# Export from SQLite to CSV
sqlite3 -header -csv "$DB_PATH" \
"SELECT played_at, track_id FROM plays ORDER BY played_at DESC;" \
> "$CSV_PATH"

# Commit and push to GitHub
git pull origin $GIT_BRANCH >> "$LOG_PATH" 2>&1
git add "$CSV_PATH"
git commit -m "$COMMIT_MSG" >> "$LOG_PATH" 2>&1 || echo "No changes to commit" >> "$LOG_PATH"
git push origin $GIT_BRANCH >> "$LOG_PATH" 2>&1

echo "Export and push completed at $(date)" >> "$LOG_PATH"


