from pathlib import Path

from typer.testing import CliRunner

from bridge_ai.cli import app

SAMPLE = Path(__file__).parent / "fixtures"
runner = CliRunner()


def test_import_players_stats(tmp_path):
    out = tmp_path / "h.parquet"
    r = runner.invoke(app, ["import", str(SAMPLE), "--out", str(out)])
    assert r.exit_code == 0, r.output
    assert "3 unique hands" in r.output
    r = runner.invoke(app, ["players", "--dataset", str(out)])
    assert "Alice" in r.output and "Carol" in r.output
    r = runner.invoke(app, ["stats", "--player", "carol", "--dataset", str(out)])
    assert r.exit_code == 0, r.output
    assert "Hands: 3" in r.output
    assert "Declared: 2" in r.output


def test_stats_unknown_player_and_missing_dataset(tmp_path):
    out = tmp_path / "h.parquet"
    runner.invoke(app, ["import", str(SAMPLE), "--out", str(out)])
    assert runner.invoke(app, ["stats", "--player", "zed", "--dataset", str(out)]).exit_code == 1
    assert runner.invoke(app, ["players", "--dataset", str(tmp_path / "no.parquet")]).exit_code == 1
