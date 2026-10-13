import subprocess

import pytest

from spotify_history import config
from spotify_history.db.migrate import migrate


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A freshly migrated database that the application code will use."""
    path = tmp_path / "plays.db"
    monkeypatch.setattr(config, "DB_PATH", path)
    monkeypatch.setattr(config, "LEGACY_DB_PATH", tmp_path / "legacy" / "plays.db")
    migrate(db_path=path)
    return path


@pytest.fixture(autouse=True)
def no_real_s3(monkeypatch):
    """Safety net: no test may shell out (e.g. `aws s3 cp`) or see an S3 bucket.

    Tests that exercise the upload path replace subprocess.run with their own fake.
    """
    monkeypatch.setattr(config, "S3_BUCKET", None)

    def _blocked(*args, **kwargs):
        raise AssertionError(f"test attempted to run a real subprocess: {args!r}")

    monkeypatch.setattr(subprocess, "run", _blocked)
