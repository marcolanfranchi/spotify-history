"""Single source of truth for settings and filesystem paths.

All runtime state (database, CSV export, log, OAuth token) lives under DATA_DIR,
resolved from the project root so it never depends on the current working directory.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
MIGRATIONS_DIR = PROJECT_ROOT / "migrations"

DB_NAME = os.getenv("SQLITE_DB_NAME", "plays.db")
DB_PATH = DATA_DIR / DB_NAME
CSV_PATH = DATA_DIR / "plays.csv"
API_DIR = DATA_DIR / "api" / "v1"  # JSON tables for the website
LOG_PATH = DATA_DIR / "spotify.log"
TOKEN_PATH = DATA_DIR / ".spotify_token"

# Pre-restructure location of the database, used only to catch a missed move.
LEGACY_DB_PATH = PROJECT_ROOT / "db" / DB_NAME

# Spotify
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
SPOTIFY_SCOPE = "playlist-read-private user-library-read user-read-recently-played"

# Email
EMAIL_TO = os.getenv("NOTIFY_EMAIL")
EMAIL_FROM = os.getenv("EMAIL_FROM")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

# Optional S3 export
S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = os.getenv("S3_PREFIX", "")
AWS_REGION = os.getenv("AWS_REGION")
