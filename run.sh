#!/bin/bash
set -e

echo "Initializing database..."
python3 scripts/init_db.py

echo "Installing cron jobs..."
bash scripts/fetch_spotify.sh
bash scripts/send_email.sh

echo "Now, fetching last 50 plays to start..."
sh -c "./venv/bin/python3 ./src/fetch_spotify.py"

echo "All done!"
echo "Your spotify plays will updated in the sqlite db every 10 minutes."
echo "You will receive a daily email with listening history and summary stats every day at midnight."
echo "You can view logs at $(pwd)/spotify.log"

