"""Regenerate docs/examples/ from the local (gitignored) dataset.

    uv run python scripts/make_examples.py --player <BBO username> --name "Zia"

Picks a few illustrative hands by fixed rules, anonymises every other player as
Partner/LHO/RHO, and writes Markdown. Only these curated pages are committed.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer

from bridge_ai import analysis as an
from bridge_ai import ddbench as dd
from bridge_ai.render import SYMBOL, example_markdown
from bridge_ai.stats import player_hands

OUT = Path("docs/examples")
ORD = {1: "first", 2: "second", 3: "third", 4: "fourth"}


def load(cache: Path) -> pd.DataFrame:
    dd_cache = cache.with_name("hands_dd.pkl")
    if dd_cache.exists():
        return pd.read_pickle(dd_cache)
    df = dd.add_double_dummy(pd.read_parquet(cache))
    df.to_pickle(dd_cache)
    return df


def fmt_call(call: str) -> str:
    return f"{call[0]}{SYMBOL[call[1]]}" if call[1] != "N" else f"{call[0]}NT"


def pick_psychs(df: pd.DataFrame, player: str, n: int = 3) -> list[tuple[str, str, str]]:
    op = an.psychs(an.openings(df, player))
    op = op[op["hcp"] <= 6].sort_values(["hcp", "hand_id"]).drop_duplicates("call").head(n)
    picks = []
    for _, o in op.iterrows():
        note = (
            f"Opened {fmt_call(o['call'])} in {ORD[o['seat_no']]} seat with just {o['hcp']} HCP "
            f"({o['shape']} shape, unalerted): a probable psych."
        )
        picks.append((o["hand_id"], "Probable psych", note))
    return picks


def pick_declarer(pb: pd.DataFrame, n: int = 3) -> list[tuple[str, str, str]]:
    h = pb[(pb["opponents"] == "humans") & pb["is_declarer"]]
    h = h[(h["tricks"] >= h["level"] + 6) & (h["dd_tricks"] < h["level"] + 6)]
    h = h.sort_values(["tricks_vs_dd", "hand_id"], ascending=[False, True]).head(n)
    return [
        (
            r["hand_id"],
            "Beat double dummy as declarer",
            f"Made {int(r['tricks'])} tricks in {fmt_call(r['contract'])} where double dummy "
            f"allows only {int(r['dd_tricks'])}: the defence slipped somewhere.",
        )
        for _, r in h.iterrows()
    ]


def pick_swings(pb: pd.DataFrame) -> list[tuple[str, str, str]]:
    h = pb[pb["opponents"] == "humans"].sort_values(["imps_vs_par", "hand_id"])
    picks = []
    for kind, r in (("best", h.iloc[-1]), ("worst", h.iloc[0])):
        note = (
            f"{int(r['imps_vs_par']):+d} IMPs against par: scored {int(r['my_score']):+d} "
            f"where par was {int(r['par_mine']):+d}."
        )
        title = "Big gain against par" if kind == "best" else "Big loss against par"
        picks.append((r["hand_id"], title, note))
    return picks


def main(
    player: str = typer.Option(..., help="BBO username"),
    name: str = typer.Option("Zia", help="Display name for the player in the diagrams"),
    cache: Path = typer.Option(Path(".cache/hands.parquet")),
) -> None:
    df = load(cache)
    pb = dd.player_benchmark(df, player)
    picks, seen = [], set()
    for pick in pick_psychs(df, player) + pick_declarer(pb) + pick_swings(pb):
        if pick[0] not in seen:
            seen.add(pick[0])
            picks.append(pick)
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.md"):
        old.unlink()
    index = [
        f"# Example hands\n\nA few hands played by {name}, from his public BBO records. "
        "Every other player is anonymised as **Partner**, **LHO** (left-hand opponent) or **RHO**. "
        f"{name} always sits at the bottom. `*` marks an alerted call.\n"
    ]
    mine = player_hands(df, player).set_index("hand_id")
    for i, (hand_id, title, note) in enumerate(picks, 1):
        row = mine.loc[hand_id]
        index.append(example_markdown(f"{i}. {title}", note, row, row["seat"], name))
    (OUT / "README.md").write_text("\n".join(index), encoding="utf-8")
    typer.echo(f"Wrote {len(picks)} examples to {OUT}/README.md")


if __name__ == "__main__":
    typer.run(main)
