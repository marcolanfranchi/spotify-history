# spotify-history

Archive your Spotify listening history into a lightweight SQLite3 database and receive daily listening summaries by email.

- Every **10 minutes**, a job ([here](src/spotify_history/jobs/fetch.py)) runs via cron to fetch your recent Spotify listening history and insert new plays into the SQLite3 database.
- Every day at **12:02 AM**, another job ([here](src/spotify_history/jobs/daily_email.py)) runs via cron to query the database, compute daily overview metrics, and send you an email summary of your listening activity.
- Every **30 minutes**, an optional job ([here](src/spotify_history/jobs/export.py)) exports `plays.csv` and uploads it to S3 if configured.

## Project Layout

```
src/spotify_history/   application package (config, auth, client, db/, jobs/)
migrations/            versioned SQL schema files (V<n>__name.sql)
scripts/               one cron installer per job (fetch_spotify.sh, send_email.sh, push_data.sh, enrich_data.sh)
run.sh                 one-shot setup: migrate, first fetch, install all cron jobs
tests/                 pytest suite
data/                  runtime state, gitignored: plays.db, plays.csv, spotify.log, .spotify_token
```

Everything runs through one entry point: `python -m spotify_history <fetch|email|export|enrich|migrate>`.


## Example Data

Your listening history is saved in a local SQLite database (`data/plays.db` by default).
Here's a simple query and sample output:

```bash
sqlite3 data/plays.db "SELECT played_at, track_name, artist_name, album_name FROM plays ORDER BY played_at DESC LIMIT 5;"
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

### 4. Create Virtual Environment & Install the Package
```bash
python3 -m venv .venv       # a virtualenv named `venv` also works
source .venv/bin/activate
pip install -e .            # add ".[dev]" for pytest and ruff
```

### 5. Initialize the Service
```bash
./run.sh
```
This script will:
- Create or upgrade the SQLite database in `data/` (named by `SQLITE_DB_NAME` in `.env`), applying any pending files from [migrations/](migrations/)
- Run a first fetch (prompting you to authorize Spotify the first time)
- Install the cron jobs by running each script in [scripts/](scripts/) (you can also re-run any one on its own)
- Once the script completes, the service is fully installed and running.

### Upgrading from the pre-package layout
If you have an existing `db/plays.db` from an older checkout, move it (and your Spotify token) into `data/` before the first run, otherwise `migrate` refuses to create a new empty DB:
```bash
mkdir -p data
mv db/plays.db data/plays.db
mv .spotify_token data/.spotify_token   # re-authorizing also works if you can't find it
```
`migrate` recognizes the existing database and keeps all of its data.

## Artist Genres & Album Details (Enrichment)

Besides raw plays, the database has normalized `artists`, `albums`, `tracks`, `track_artists` (all artists on a track) and `artist_genres` tables.

- **New plays** are written to all of these automatically by `fetch`, at no extra API cost. Albums seen this way already have release date, type and track count; tracks get `explicit`, `isrc`, track/disc numbers; plays get `context_type` (playlist / album / artist).
- **Artist genres and images** need one API call per artist (`GET /artists/{id}`; Spotify removed the batch endpoint). The `enrich` command fills these in:

```bash
python -m spotify_history enrich --limit 50              # up to 50 API calls: artists first, then albums
python -m spotify_history enrich --only artists --limit 100
```

It works through a queue (rows with `enriched_at IS NULL`), most-played artists first. Each run is bounded by `--limit`, throttled, and safe to stop and re-run, so a one-time backfill of existing history can be done in small batches over several days. If Spotify rate limits (429) the run stops cleanly and keeps its progress. Check what's left with:

```bash
sqlite3 data/plays.db "SELECT 'artists', COUNT(*) FROM artists WHERE enriched_at IS NULL UNION ALL SELECT 'albums', COUNT(*) FROM albums WHERE enriched_at IS NULL;"
```

To keep new artists enriched automatically once the backfill is done, install the hourly job (20 calls per run). It is not installed by `run.sh`:

```bash
bash scripts/enrich_data.sh
```

Example queries:

```sql
-- top genres by plays
SELECT g.genre, COUNT(*) AS plays
FROM plays p JOIN artist_genres g ON g.artist_id = p.artist_id
GROUP BY g.genre ORDER BY plays DESC LIMIT 10;

-- plays per release year
SELECT substr(al.release_date, 1, 4) AS year, COUNT(*) AS plays
FROM plays p JOIN albums al ON al.id = p.album_id
GROUP BY year ORDER BY year;
```

`artists.popularity` and `followers_total` are stored when Spotify returns them, but Spotify has deprecated both fields, so treat them as best-effort (they can become NULL).

## Monitoring & Logs
Logs from the cron-scheduled jobs are written to `data/spotify.log`:
```bash
tail -f data/spotify.log
```

## Development
```bash
pip install -e ".[dev]"
pytest
ruff check .
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

When `S3_BUCKET` is set, the export job (`python -m spotify_history export --upload`, run by cron every 30 minutes) writes the plays table from SQLite to `data/plays.csv` and uploads it to `s3://your-bucket-name/spotify-history/plays.csv`. Running `python -m spotify_history export` by hand only writes the local CSV; it never uploads unless you pass `--upload`.

The S3 export is independent of everything else. It has no effect on data collection or the daily email.
