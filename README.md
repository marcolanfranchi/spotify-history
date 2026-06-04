# spotify-history

Archive your Spotify listening history into a lightweight SQLite3 database and receive daily listening summaries by email.

- Every **10 minutes**, a Python script ([here](src/fetch_spotify.py)) runs via cron to fetch your recent Spotify listening history and upsert it into the SQLite3 database.
- Every day at **midnight (12:01 AM)**, another Python script ([here](src/send_email.py)) runs via cron to query the database, compute daily overview metrics, and send you an email summary of your listening activity.


## Example Data

Your listening history is saved in a local SQLite database (`plays.db` by default).
Here's a simple query and sample output:

```bash
sqlite3 db/plays.db "SELECT played_at, track_name, artist_name, album_name FROM plays ORDER BY played_at DESC LIMIT 5;"
```
Output:
```yaml
played_at                 track_name      artist_name      album_name
==================================================================================
2025-08-19T20:57:21.365Z  Hard Time       Weiland          Vices
2025-08-19T20:54:07.984Z  Or              Tek lintowe      I am a evil person
2025-08-19T20:48:32.962Z  Door            Laker            Door
2025-08-19T20:45:51.678Z  Crash           Alleen Plains    Fall From Grace
2025-08-19T20:45:09.232Z  All The Same    Weiland          Vices
```

## Requirements

### Operating System
- Supported: **macOS** and **Linux**
- The service must run on a host that remains continuously powered and connected (e.g., dedicated server, VM, or Raspberry Pi).
  - For example, I'm running it from a Raspberry Pi Model B v1.1 (512MB RAM) running Raspberry Pi OS Lite (32-bit).

### Runtime & Dependencies
- **Python 3.11**
- **SQLite3**
- [Spotipy](https://spotipy.readthedocs.io/en/2.25.1/) (Spotify Web API client for Python)
- **Cron** (for scheduling)
- **Shell scripting**
- [smtplib](https://docs.python.org/3/library/smtplib.html) (built-in Python SMTP client)

## Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/marcolanfranchi/spotify-history
cd spotify-history
```

### 2. Configure Environment Variables
Copy the example environment file and fill in your own values:
```bash
cp .env.example .env
```
Update `.env` with your configuration:
```bash
# Spotify API
SPOTIFY_CLIENT_ID=abcdefg123456789
SPOTIFY_CLIENT_SECRET=abcdefg123456789
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback

# SQLite
SQLITE_DB_NAME=plays.db

# Email notifications
NOTIFY_EMAIL=example@gmail.com
EMAIL_FROM=example@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=example@gmail.com
SMTP_PASS=example
```

### 3. Install SQLite (if not already installed)
```bash
sudo apt-get update
sudo apt-get install sqlite3 -y
```

### 4. Create Virtual Environment & Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Initialize the Service
```bash
chmod +x ./run.sh
./run.sh
```
This script will:
- Create the SQLite database (if not already present) at [db/](db/) with the name `SQLITE_DB_NAME` (from `.env`)
- Apply the latest schema version from [db/sql/](db/sql/)
- Set up the required cron jobs
- Once the script completes, the service is fully installed and running.

## Monitoring & Logs
Logs from the cron-scheduled scripts are written to `spotify.log` in the project root:
```bash
cat spotify.log
```

## Optional: S3 Export

By default the project is entirely local with all data going into the SQLite db. If you want `plays.csv` uploaded to an S3 bucket on a schedule, you can enable this optionally.

### 1. Install and configure the AWS CLI

```bash
# macOS
brew install awscli

# Raspberry Pi / Debian
sudo apt-get install awscli -y
```

Then configure it with your IAM user credentials:
```bash
aws configure
```

You'll be prompted for your AWS Access Key ID, Secret Access Key, default region, and output format.

### 2. Set the S3 variables in your `.env`

Uncomment and fill in the S3 block at the bottom of `.env`:
```bash
S3_BUCKET=your-bucket-name
S3_PREFIX=spotify-history   # folder inside the bucket, no trailing slash
AWS_REGION=us-east-2
```

### How it works

When `S3_BUCKET` is set, the cron job running `src/export_to_s3.sh` every 30 minutes will export the full plays table from SQLite to `data/plays.csv` and upload it to `s3://your-bucket-name/spotify-history/plays.csv`..

The S3 export is independent of everything else. It has no effect on data collection or the daily email.
