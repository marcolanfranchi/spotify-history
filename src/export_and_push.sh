#!/bin/bash
# Get absolute path to the script’s directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

DB_PATH="$PROJECT_DIR/db/plays.db"
CSV_PATH="$PROJECT_DIR/data/plays.csv"
LOG_PATH="$PROJECT_DIR/spotify.log"

# Ensure all output goes to the single log file
exec >> "$LOG_PATH" 2>&1

# Move into the repo so git works
cd "$PROJECT_DIR" || { echo "Failed to cd into $PROJECT_DIR"; exit 1; }

# Git info
GIT_BRANCH="main"
COMMIT_MSG="Exported plays.csv on $(date '+%Y-%m-%d %H:%M:%S') (automated)"

# Export from SQLite to CSV
sqlite3 -header -csv "$DB_PATH" \
"SELECT played_at, track_id, track_name, artist_name FROM plays ORDER BY played_at DESC;" \
> "$CSV_PATH"

# Pull latest changes
git pull origin "$GIT_BRANCH"

# Stage file
git add "$CSV_PATH"

# Commit with bot identity
GIT_AUTHOR_NAME="pi-bot" \
GIT_AUTHOR_EMAIL="pi-bot@invalid.invalid" \
GIT_COMMITTER_NAME="pi-bot" \
GIT_COMMITTER_EMAIL="pi-bot@invalid.invalid" \
git commit -m "$COMMIT_MSG" || echo "No changes to commit"

# Push as usual (using your SSH key)
git push origin "$GIT_BRANCH"

echo "Export and push completed at $(date)"
