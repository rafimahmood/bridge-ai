from pathlib import Path

import pytest

from bridge_ai.dataset import build_dataset
from bridge_ai.ddbench import add_double_dummy, benchmark, imps, player_benchmark, summary

SAMPLE = Path(__file__).parent / "fixtures" / "sample_myhands.html"


@pytest.mark.parametrize(
    ("diff", "expected"),
    [(0, 0), (10, 0), (20, 1), (-20, -1), (50, 2), (420, 9), (-450, -10), (1000, 14), (6000, 24)],
)
def test_imps(diff, expected):
    assert imps(diff) == expected


def test_double_dummy_columns_and_consistency():
    df, _ = build_dataset([SAMPLE])
    dd = add_double_dummy(df)
    assert len(dd) == 3
    for table in dd["dd_table"]:
        assert set(table) == {f"{d}{p}" for d in "SHDCN" for p in "NESW"}
        # tricks are per declarer (the lead differs), but always within 0..13
        assert all(0 <= v <= 13 for v in table.values())
    # passed out hand has no declarer trick count
    assert dd.iloc[1]["dd_tricks"] is None or dd.iloc[1]["dd_tricks"] != dd.iloc[1]["dd_tricks"]
    # par is a legal duplicate score or zero
    assert all(isinstance(p, int) for p in dd["par_ns"])


def test_benchmark_and_player_summary():
    df, _ = build_dataset([SAMPLE])
    dd = add_double_dummy(df)
    bench = benchmark(dd)
    assert len(bench) == 2  # pass-out dropped
    assert (bench["tricks_vs_dd"] == bench["tricks"] - bench["dd_tricks"]).all()
    pb = player_benchmark(dd, "carol")
    assert len(pb) == 2
    assert {"par_mine", "dd_mine", "vs_par", "imps_vs_par"} <= set(pb.columns)
    s = summary(pb)
    assert s["hands"] == 2
