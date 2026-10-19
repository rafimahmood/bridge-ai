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


def test_player_counts_merge_case_variants():
    import pandas as pd

    from bridge_ai.stats import player_counts

    df = pd.DataFrame(
        {"player_N": ["Ann", "ann"], "player_E": ["GiB", "GiB"], "player_S": ["Bo", "Bo"],
         "player_W": ["Cy", "Cy"]}
    )  # fmt: skip
    counts = player_counts(df)
    assert counts["Ann"] == 2 and "GiB" not in counts.index


def test_benchmark_command(tmp_path):
    out = tmp_path / "h.parquet"
    runner.invoke(app, ["import", str(SAMPLE), "--out", str(out)])
    r = runner.invoke(app, ["benchmark", "--player", "carol", "--dataset", str(out)])
    assert r.exit_code == 0, r.output
    assert "Hands benchmarked: 2" in r.output
