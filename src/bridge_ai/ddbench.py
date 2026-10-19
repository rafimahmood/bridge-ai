"""Double-dummy and par benchmark using endplay."""

from __future__ import annotations

import bisect

import pandas as pd
from endplay.dds import calc_all_tables, par
from endplay.types import Deal, Denom, Player, Vul

from .analysis import SEATS
from .scoring import score
from .stats import player_hands

DENOMS = {"S": Denom.spades, "H": Denom.hearts, "D": Denom.diamonds, "C": Denom.clubs,
          "N": Denom.nt}  # fmt: skip
PLAYERS = {"N": Player.north, "E": Player.east, "S": Player.south, "W": Player.west}
VULS = {"None": Vul.none, "NS": Vul.ns, "EW": Vul.ew, "Both": Vul.both}
IMP_BOUNDS = [20, 50, 90, 130, 170, 220, 270, 320, 370, 430, 500, 600, 750, 900, 1100, 1300,
              1500, 1750, 2000, 2250, 2500, 3000, 3500, 4000]  # fmt: skip


def imps(diff: int) -> int:
    """Convert a score difference to IMPs (signed)."""
    n = bisect.bisect_right(IMP_BOUNDS, abs(diff))
    return n if diff >= 0 else -n


def _deal(row: pd.Series) -> Deal:
    return Deal(
        "N:" + " ".join(row[f"hand_{s}"] for s in SEATS)
    )  # N, E, S, W order matches SEATS "NESW"


def add_double_dummy(df: pd.DataFrame, batch: int = 8) -> pd.DataFrame:
    """Add dd_tricks (declarer, actual strain), par_ns and the full DD table per deal."""
    out = df.copy()
    tricks, par_ns, tables = [], [], []
    for start in range(0, len(out), batch):
        chunk = out.iloc[start : start + batch]
        deals = [_deal(r) for _, r in chunk.iterrows()]
        for (_, r), tab in zip(chunk.iterrows(), calc_all_tables(deals), strict=True):
            tables.append({f"{d}{p}": tab[DENOMS[d], PLAYERS[p]] for d in "SHDCN" for p in SEATS})
            pl = par(tab, VULS[r["vulnerability"]], PLAYERS[r["dealer"]])
            par_ns.append(pl.score)
            if r["contract"] == "PASS" or pd.isna(r["declarer"]):
                tricks.append(None)
            else:
                tricks.append(tab[DENOMS[r["strain"]], PLAYERS[r["declarer"]]])
    out["dd_tricks"] = tricks
    out["par_ns"] = par_ns
    out["dd_table"] = tables
    return out


def benchmark(df_dd: pd.DataFrame) -> pd.DataFrame:
    """Per-hand comparison of actual result against double dummy at the same contract."""
    d = df_dd[df_dd["dd_tricks"].notna() & df_dd["tricks"].notna()].copy()
    d["dd_tricks"] = d["dd_tricks"].astype(int)
    d["tricks_vs_dd"] = d["tricks"] - d["dd_tricks"]

    def dd_score(r: pd.Series) -> int:
        vul = r["vulnerability"] == "Both" or (
            r["vulnerability"] == ("NS" if r["declarer"] in "NS" else "EW")
        )
        pts = score(int(r["level"]), r["strain"], r["doubled"], vul, int(r["dd_tricks"]))
        return pts if r["declarer"] in "NS" else -pts

    d["dd_ns_score"] = d.apply(dd_score, axis=1)
    return d


def player_benchmark(df_dd: pd.DataFrame, name: str) -> pd.DataFrame:
    """Benchmark rows for `name`, with scores from the player's side."""
    bench = benchmark(df_dd)
    ph = player_hands(bench, name)
    sign = ph["seat"].map(lambda s: 1 if s in "NS" else -1)
    ph["par_mine"] = ph["par_ns"] * sign
    ph["dd_mine"] = ph["dd_ns_score"] * sign
    ph["vs_dd"] = ph["my_score"] - ph["dd_mine"]
    ph["vs_par"] = ph["my_score"] - ph["par_mine"]
    ph["imps_vs_par"] = ph["vs_par"].map(imps)
    ph["imps_vs_dd"] = ph["vs_dd"].map(imps)
    return ph


def summary(pb: pd.DataFrame) -> dict:
    decl = pb[pb["is_declarer"]]
    defend = pb[~pb["is_declarer"] & ~pb["is_dummy"]]
    return {
        "hands": len(pb),
        "avg_imps_vs_par": round(float(pb["imps_vs_par"].mean()), 2),
        "declarer_tricks_vs_dd": round(float(decl["tricks_vs_dd"].mean()), 2)
        if len(decl)
        else None,
        "declarer_beat_or_equal_dd_pct": round(100 * (decl["tricks_vs_dd"] >= 0).mean(), 1)
        if len(decl)
        else None,
        "defence_held_dd_pct": round(100 * (defend["tricks_vs_dd"] <= 0).mean(), 1)
        if len(defend)
        else None,
        "par_matched_pct": round(100 * (pb["vs_par"] == 0).mean(), 1),
    }
