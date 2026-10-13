"""Export the plays table to data/plays.csv and, with --upload and S3_BUCKET set, upload it."""
import csv
import subprocess
import sys
from datetime import datetime

from spotify_history import config
from spotify_history.db.connection import get_conn

COLUMNS = ["played_at", "track_id", "track_name", "artist_name"]


def export_csv():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT {', '.join(COLUMNS)} FROM plays WHERE user_id = 1 ORDER BY played_at DESC;"
        ).fetchall()
    with open(config.CSV_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(tuple(r) for r in rows)
    return len(rows)


def upload_to_s3():
    key = f"{config.S3_PREFIX}/plays.csv" if config.S3_PREFIX else "plays.csv"
    dest = f"s3://{config.S3_BUCKET}/{key}"
    cmd = ["aws", "s3", "cp", str(config.CSV_PATH), dest]
    if config.AWS_REGION:
        cmd += ["--region", config.AWS_REGION]
    result = subprocess.run(cmd, check=False)
    status = "succeeded" if result.returncode == 0 else "failed"
    print(f"S3 upload {status}: {dest} at {datetime.now().astimezone()}")
    return result.returncode


def run(upload=False):
    """Write the CSV; upload it only when explicitly asked (cron passes --upload).

    Manual runs, scripts and tests therefore never touch S3 just because
    S3_BUCKET happens to be set in .env.
    """
    count = export_csv()
    print(f"Exported {count} plays to {config.CSV_PATH}")
    if not upload:
        print("Skipping S3 upload (pass --upload to enable)")
        return 0
    if not config.S3_BUCKET:
        print("S3_BUCKET not set — skipping S3 upload")
        return 0
    return upload_to_s3()


if __name__ == "__main__":
    raise SystemExit(run(upload="--upload" in sys.argv))
