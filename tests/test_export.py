import csv
import subprocess
from types import SimpleNamespace

from spotify_history import config
from spotify_history.db.repository import insert_play, upsert_user
from spotify_history.jobs import export


def _seed(db):
    user = upsert_user("spotify-user")
    insert_play(
        user_db_id=user, track_id="t1", track_name="Song", artist_id="a1",
        artist_name="Artist", album_id="al1", album_name="Album",
        played_at="2025-08-19T20:57:21.365Z", duration_ms=1000, context_uri=None,
    )


def _use_tmp_data_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "CSV_PATH", tmp_path / "plays.csv")


def _record_aws_calls(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_export_writes_csv(db, tmp_path, monkeypatch):
    _seed(db)
    _use_tmp_data_dir(monkeypatch, tmp_path)

    assert export.run() == 0

    with open(config.CSV_PATH, newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["played_at", "track_id", "track_name", "artist_name"]
    assert rows[1] == ["2025-08-19T20:57:21.365Z", "t1", "Song", "Artist"]


def test_export_does_not_upload_by_default_even_with_bucket_set(db, tmp_path, monkeypatch):
    """Regression: a manual export must never hit S3 just because S3_BUCKET is in .env."""
    _seed(db)
    _use_tmp_data_dir(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "S3_BUCKET", "real-prod-bucket")
    calls = _record_aws_calls(monkeypatch)

    export.run()

    assert calls == []


def test_upload_flag_without_bucket_does_nothing(db, tmp_path, monkeypatch):
    _seed(db)
    _use_tmp_data_dir(monkeypatch, tmp_path)
    calls = _record_aws_calls(monkeypatch)

    export.run(upload=True)

    assert calls == []


def test_upload_flag_with_bucket_builds_expected_command(db, tmp_path, monkeypatch):
    """The upload path is exercised against a fake `aws`; nothing leaves the machine."""
    _seed(db)
    _use_tmp_data_dir(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "S3_BUCKET", "test-bucket")
    monkeypatch.setattr(config, "S3_PREFIX", "test-prefix")
    monkeypatch.setattr(config, "AWS_REGION", "us-test-1")
    calls = _record_aws_calls(monkeypatch)

    assert export.run(upload=True) == 0

    assert calls == [[
        "aws", "s3", "cp", str(config.CSV_PATH),
        "s3://test-bucket/test-prefix/plays.csv", "--region", "us-test-1",
    ]]
