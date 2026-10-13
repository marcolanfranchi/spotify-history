import smtplib
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

from dateutil import parser
from tzlocal import get_localzone

from spotify_history import config
from spotify_history.db.repository import get_plays_between

ISO_UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def get_yesterdays_plays():
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=1)

    rows = get_plays_between(start.strftime(ISO_UTC_FORMAT), end.strftime(ISO_UTC_FORMAT))

    local_tz = get_localzone()

    plays = [
        {
            "played_at": (
                parser.isoparse(row["played_at"])
                .replace(tzinfo=timezone.utc)
                .astimezone(local_tz)
                .strftime("%b %d, %Y %I:%M %p %Z")
            ),
            "track_name": row["track_name"],
            "album_name": row["album_name"],
            "artist_names": [row["artist_name"]]  # keep as list
        }
        for row in rows
    ]

    track_counter = Counter(p["track_name"] for p in plays)
    artist_counter = Counter(p["artist_names"][0] for p in plays)
    album_counter = Counter(p["album_name"] for p in plays)

    analytics = {
        "top_tracks": track_counter.most_common(3),
        "top_artists": artist_counter.most_common(3),
        "top_albums": album_counter.most_common(3),
        "unique_tracks": len(track_counter),
        "unique_artists": len(artist_counter),
        "unique_albums": len(album_counter),
    }

    return plays, start, end, analytics

def send_email(plays, start, end, analytics):
    line_width = 20
    summary_lines = [
        f"Spotify Daily Summary for {start.date()} to {end.date()}",
        "-" * line_width,
        f"  Unique tracks: {analytics['unique_tracks']}",
        f"  Unique artists: {analytics['unique_artists']}",
        f"  Unique albums: {analytics['unique_albums']}",
        "-" * line_width,
        "Top Tracks:",
    ]
    for track, count in analytics["top_tracks"]:
        artist = next((p['artist_names'][0] for p in plays if p['track_name'] == track), "Unknown Artist")
        summary_lines.append(f"  {artist} - {track} ({count} plays)")
    summary_lines.append("-"*line_width)
    summary_lines.append("Top Artists:")
    for artist, count in analytics["top_artists"]:
        summary_lines.append(f"  {artist} ({count} plays)")
    summary_lines.append("-"*line_width)
    summary_lines.append("Top Albums:")
    for album, count in analytics["top_albums"]:
        summary_lines.append(f"  {album} ({count} plays)")
    summary_lines.append("-"*line_width)
    summary_lines.append("All Plays:")
    for p in plays:
        artists = ", ".join(p['artist_names'])
        line = f"{p['played_at']} — {p['track_name']} — {artists} — {p['album_name']}"
        summary_lines.append(line)

    summary_text = "\n".join(summary_lines)

    msg = MIMEText(summary_text)
    msg['Subject'] = f"Spotify Daily Summary {start.date()}"
    msg['From'] = config.EMAIL_FROM
    msg['To'] = config.EMAIL_TO

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
        server.starttls()
        server.login(config.SMTP_USER, config.SMTP_PASS)
        server.send_message(msg)

def run():
    plays, start, end, analytics = get_yesterdays_plays()
    # if no plays, skip sending email
    if not plays:
        print("No plays yesterday.")
        return
    # otherwise, send the email
    send_email(plays, start, end, analytics)

if __name__ == "__main__":
    run()

