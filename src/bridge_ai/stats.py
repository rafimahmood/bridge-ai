"""Per-player views and summaries over the hands table."""

from __future__ import annotations

import pandas as pd

SEATS = "NESW"
PARTNER = {"N": "S", "S": "N", "E": "W", "W": "E"}
ROBOTS = {"gib", ""}


def is_robot(df: pd.DataFrame, seats: list[str]) -> pd.Series:
    """True where any of the given seats is a BBO robot (GiB)."""
    flags = [df[f"player_{s}"].str.lower() == "gib" for s in seats]
    return pd.concat(flags, axis=1).any(axis=1)


def player_counts(df: pd.DataFrame, include_robots: bool = False) -> pd.Series:
    names = pd.concat([df[f"player_{s}"] for s in SEATS])
    key = names.str.lower()
    display = names.groupby(key).agg(lambda x: x.value_counts().index[0])
    counts = key.value_counts()
    counts.index = counts.index.map(display)
    if not include_robots:
        counts = counts[~counts.index.str.lower().isin(ROBOTS)]
    return counts


def player_hands(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """One row per (hand, seat) where `name` sat; adds seat, partner, side, my_score."""
    frames = []
    for seat in SEATS:
        sub = df[df[f"player_{seat}"].str.lower() == name.lower()].copy()
        sub["seat"] = seat
        sub["partner"] = sub[f"player_{PARTNER[seat]}"]
        sub["side"] = "NS" if seat in "NS" else "EW"
        sign = 1 if seat in "NS" else -1
        sub["my_score"] = sub["ns_score"] * sign
        sub["is_declarer"] = sub["declarer"] == seat
        sub["is_dummy"] = sub["declarer"] == PARTNER[seat]
        opps = [x for x in SEATS if x not in (seat, PARTNER[seat])]
        sub["opponents"] = is_robot(sub, opps).map({True: "robots", False: "humans"})
        sub["partner_is_robot"] = sub[f"player_{PARTNER[seat]}"].str.lower() == "gib"
        frames.append(sub)
    out = pd.concat(frames) if frames else df.iloc[0:0]
    return out.sort_values(["date", "time"]).reset_index(drop=True)


def summarise(df: pd.DataFrame, name: str) -> dict:
    ph = player_hands(df, name)
    if ph.empty:
        return {}
    played = ph[ph["contract"] != "PASS"]
    decl = played[played["is_declarer"]]
    made = decl["tricks"] >= decl["level"] + 6
    return {
        "hands": len(ph),
        "first_date": ph["date"].min(),
        "last_date": ph["date"].max(),
        "by_seat": ph["seat"].value_counts().to_dict(),
        "by_event": ph["event_type"].value_counts().to_dict(),
        "partners": ph["partner"].value_counts().head(5).to_dict(),
        "passed_out": int((ph["contract"] == "PASS").sum()),
        "declared": len(decl),
        "declared_made_pct": round(100 * made.mean(), 1) if len(decl) else None,
        "avg_score": round(played["my_score"].mean(), 1) if len(played) else None,
        "top_contracts_declared": decl["contract"].value_counts().head(5).to_dict(),
    }
