import os
import sqlite3
import smtplib
from dotenv import load_dotenv
from email.mime.text import MIMEText
from datetime import datetime, timedelta

load_dotenv()

DB_NAME = os.getenv("SQLITE_DB_NAME", "plays.db")
DB_PATH = os.path.join("db", DB_NAME)

EMAIL_TO = os.getenv("NOTIFY_EMAIL")
EMAIL_FROM = os.getenv("EMAIL_FROM")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

def get_yesterdays_plays():
    yesterday = datetime.utcnow().date() - timedelta(days=1)
    start = datetime.combine(yesterday, datetime.min.time())
    end = datetime.combine(yesterday, datetime.max.time())

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT played_at, track_name, album_name, artist_name
        FROM plays
        WHERE played_at >= ? AND played_at < ?
        ORDER BY played_at ASC
    """, (start, end))

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "played_at": row["played_at"],
            "track_name": row["track_name"],
            "album_name": row["album_name"],
            "artist_names": [row["artist_name"]]  # keep list for compatibility
        }
        for row in rows
    ]

def send_email(summary_text):
    msg = MIMEText(summary_text)
    msg['Subject'] = f"Spotify Daily Summary {datetime.utcnow().date()}"
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)

def run():
    plays = get_yesterdays_plays()
    if not plays:
        print("No plays yesterday.")
        return

    lines = []
    for p in plays:
        artists = ", ".join(p['artist_names'])
        line = f"{p['played_at']} — {p['track_name']} — {artists} — {p['album_name']}"
        lines.append(line)

    summary_text = "\n".join(lines)
    send_email(summary_text)

if __name__ == "__main__":
    run()
