#!/bin/bash
set -e

echo "Initializing database..."
python3 scripts/init_db.py

echo "Installing cron jobs..."
bash scripts/fetch_spotify.sh
bash scripts/send_email.sh

echo "All done! Logs at $(pwd)/spotify.log"
