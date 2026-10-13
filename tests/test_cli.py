import pytest

from spotify_history import __main__ as cli


def test_upload_flag_rejected_for_other_commands():
    with pytest.raises(SystemExit):
        cli.main(["fetch", "--upload"])


@pytest.mark.parametrize("args", [
    ["fetch", "--limit", "5"],
    ["export", "--only", "artists"],
    ["enrich", "--limit", "0"],
    ["enrich", "--upload"],
])
def test_invalid_flag_combinations_rejected(args):
    with pytest.raises(SystemExit):
        cli.main(args)


def test_enrich_passes_limit_and_only(monkeypatch):
    seen = {}

    def fake_run(limit, only):
        seen.update(limit=limit, only=only)
        return 0

    monkeypatch.setattr("spotify_history.jobs.enrich.run", fake_run)
    assert cli.main(["enrich", "--limit", "7", "--only", "albums"]) == 0
    assert seen == {"limit": 7, "only": "albums"}


def test_fetch_exit_code_is_zero_even_with_new_plays(monkeypatch):
    monkeypatch.setattr("spotify_history.jobs.fetch.run", lambda: 5)
    assert cli.main(["fetch"]) == 0
