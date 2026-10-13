"""Export plays.csv and the JSON tables; with --upload and S3_BUCKET set, upload them."""
import csv
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from spotify_history import config
from spotify_history.db.connection import get_conn
from spotify_history.jobs import export_json

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


def _s3_key(name):
    return f"{config.S3_PREFIX}/{name}" if config.S3_PREFIX else name


def _aws_cp(src, key, extra=()):
    dest = f"s3://{config.S3_BUCKET}/{key}"
    cmd = ["aws", "s3", "cp", str(src), dest, *extra]
    if config.AWS_REGION:
        cmd += ["--region", config.AWS_REGION]
    result = subprocess.run(cmd, check=False)
    status = "succeeded" if result.returncode == 0 else "failed"
    print(f"S3 upload {status}: {dest} at {datetime.now().astimezone()}")
    return result.returncode


def upload_to_s3():
    """Upload plays.csv (unchanged location and format)."""
    return _aws_cp(config.CSV_PATH, _s3_key("plays.csv"))


def upload_json_to_s3():
    """Upload the JSON tables gzipped (Content-Encoding: gzip, decoded by browsers).

    Data files go first and manifest.json last. Stops at the first failure so a
    manifest never advertises files that didn't make it.
    """
    extra = [
        "--content-type", "application/json",
        "--content-encoding", "gzip",
        "--cache-control", "max-age=300",
    ]
    names = [*(f"{t}.json" for t in export_json.TABLE_ORDER), "manifest.json"]
    with tempfile.TemporaryDirectory() as tmp:
        for name in names:
            gz = Path(tmp) / name
            gz.write_bytes(export_json.gzipped(config.API_DIR / name))
            rc = _aws_cp(gz, _s3_key(f"v{export_json.SCHEMA_VERSION}/{name}"), extra)
            if rc != 0:
                return rc
    return 0


def run(upload=False):
    """Write the CSV; upload it only when explicitly asked (cron passes --upload).

    Manual runs, scripts and tests therefore never touch S3 just because
    S3_BUCKET happens to be set in .env.
    """
    count = export_csv()
    print(f"Exported {count} plays to {config.CSV_PATH}")
    manifest = export_json.write_json_files()
    rows = ", ".join(f"{n}={m['rows']}" for n, m in manifest["tables"].items())
    print(f"Exported JSON tables to {config.API_DIR} ({rows})")
    if not upload:
        print("Skipping S3 upload (pass --upload to enable)")
        return 0
    if not config.S3_BUCKET:
        print("S3_BUCKET not set — skipping S3 upload")
        return 0
    # the CSV goes first and independently of the JSON, so a JSON problem can
    # never stop the existing site data from updating
    csv_rc = upload_to_s3()
    json_rc = upload_json_to_s3()
    return csv_rc or json_rc


if __name__ == "__main__":
    raise SystemExit(run(upload="--upload" in sys.argv))
