"""Opening bids, psych detection, opening leads and result patterns for one player."""

from __future__ import annotations

import pandas as pd

from .stats import PARTNER, player_hands

SEATS = "NESW"
HCP_VALUES = {"A": 4, "K": 3, "Q": 2, "J": 1}
SUIT_NAMES = "SHDC"
LEFT_OF = {"N": "E", "E": "S", "S": "W", "W": "N"}
BIG_PRE = {"3", "4", "5"}


def hcp(hand: str) -> int:
    return sum(HCP_VALUES.get(c, 0) for c in hand if c != ".")


def shape(hand: str) -> tuple[int, int, int, int]:
    """Suit lengths in S, H, D, C order."""
    s, h, d, c = (len(x) for x in hand.split("."))
    return s, h, d, c


def suit_cards(hand: str, suit: str) -> str:
    return hand.split(".")[SUIT_NAMES.index(suit)]


def is_balanced(hand: str) -> bool:
    return sorted(shape(hand)) in ([2, 3, 4, 4], [3, 3, 3, 4], [2, 3, 3, 5])


def opening_info(row: pd.Series, seat: str) -> tuple[int, str] | None:
    """(seat_number 1-4, call) if `seat` made the opening bid, else None."""
    auction = row["auction"].split()
    dealer = row["dealer"]
    for i, call in enumerate(auction):
        if call == "P":
            continue
        who = SEATS[(SEATS.index(dealer) + i) % 4]
        return (i + 1, call) if who == seat and i < 4 else None
    return None


def relative_vul(vulnerability: str, seat: str) -> str:
    """'NV', 'Vul', 'Fav' (they vul, we not) or 'Unfav' (we vul, they not)."""
    if vulnerability == "None":
        return "NV/NV"
    if vulnerability == "Both":
        return "Vul/Vul"
    ours = (vulnerability == "NS") == (seat in "NS")
    return "Vul/NV" if ours else "NV/Vul"


def opening_anomaly(hand: str, call: str, seat_no: int) -> str | None:
    """Reason a standard-system opening call looks like a psych, else None.

    Deliberately lenient (SAYC-ish) so flags are worth reading, not exhaustive.
    """
    pts = hcp(hand)
    sh = dict(zip("SHDC", shape(hand), strict=True))
    level, strain = int(call[0]), call[1]
    late = seat_no >= 3
    if level == 1 and strain == "N":
        return None if 12 <= pts <= 19 else f"1NT with {pts} HCP"
    if level == 1:
        floor = 8 if late else 10
        if pts < floor:
            return f"1{strain} with only {pts} HCP"
        if strain in "SH" and sh[strain] < 4:
            return f"1{strain} on {sh[strain]}-card suit"
        if strain in "DC" and sh[strain] < 3:
            return f"1{strain} on {sh[strain]}-card suit"
        return None
    if level == 2 and strain == "C":
        return None if pts >= 16 else f"strong 2C with {pts} HCP"
    if level == 2 and strain == "N":
        return None if 19 <= pts <= 23 else f"2NT with {pts} HCP"
    if level == 2 and strain == "D":
        return None  # 2D is very often artificial (Multi, Flannery, Roman): never flag
    if level == 2:
        if pts > 13:
            return f"weak 2{strain} with {pts} HCP"
        if sh[strain] < 5:
            return f"weak 2{strain} on {sh[strain]}-card suit"
        return None
    if level >= 3 and strain != "N":
        if pts > 13:
            return f"{call} pre-empt with {pts} HCP"
        if sh[strain] < level + 2 and level <= 4:
            return f"{call} pre-empt on {sh[strain]}-card suit"
    return None


def openings(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """One row per hand where `name` opened the bidding."""
    ph = player_hands(df, name)
    rows = []
    for _, r in ph.iterrows():
        info = opening_info(r, r["seat"])
        if info is None:
            continue
        seat_no, call = info
        hand = r[f"hand_{r['seat']}"]
        alerted = str(seat_no - 1) in str(r.get("alerted_calls", "")).split()
        rows.append(
            {
                "hand_id": r["hand_id"],
                "seat_no": seat_no,
                "call": call,
                "vul": relative_vul(r["vulnerability"], r["seat"]),
                "hcp": hcp(hand),
                "shape": "".join(map(str, shape(hand))),
                "alerted": alerted,
                # an alerted call is artificial by definition, so it is never a psych
                "anomaly": None if alerted else opening_anomaly(hand, call, seat_no),
            }
        )
    return pd.DataFrame(rows)


def opening_table(op: pd.DataFrame, by: str = "seat_no") -> pd.DataFrame:
    """Opening call frequency (share of openings) per seat number or vulnerability."""
    t = pd.crosstab(op["call"], op[by])
    return (t / t.sum()).round(3)


def psychs(op: pd.DataFrame) -> pd.DataFrame:
    return op[op["anomaly"].notna()].reset_index(drop=True)


def classify_lead(leader_hand: str, card: str, contract_strain: str, bid_suits: set[str]) -> dict:
    suit, rank = card[0], card[1]
    holding = suit_cards(leader_hand, suit)
    pos = holding.index(rank) if rank in holding else -1
    n = len(holding)
    top_of_seq = pos == 0 and n >= 2 and _adjacent(holding[0], holding[1])
    if n == 1:
        kind = "singleton"
    elif top_of_seq and rank in "AKQJT":
        kind = "top of sequence"
    elif pos == 0 and rank == "A":
        kind = "ace"
    elif pos == len(holding) - 1 and n == 2:
        kind = "doubleton (low)" if pos > 0 else "doubleton (high)"
    elif pos == 3 and n >= 4:
        kind = "fourth best"
    elif pos == n - 1 and n == 3:
        kind = "low from three"
    elif rank in "AKQJT":
        kind = "honour (other)"
    else:
        kind = "other spot card"
    return {
        "suit": suit,
        "rank": rank,
        "length": n,
        "kind": kind,
        "is_trump": suit == contract_strain,
        "is_bid_by_defence": suit in bid_suits,
        "vs": "NT" if contract_strain == "N" else "suit",
    }


def _adjacent(a: str, b: str) -> bool:
    order = "AKQJT98765432"
    return order.index(b) - order.index(a) == 1


def defensive_suits(auction: str, dealer: str, leader: str) -> set[str]:
    """Suits (not NT) bid naturally by the defending side, i.e. the leader's partnership."""
    side = {leader, PARTNER[leader]}
    out = set()
    for i, call in enumerate(auction.split()):
        who = SEATS[(SEATS.index(dealer) + i) % 4]
        if call not in {"P", "D", "R"} and call[1] != "N" and who in side:
            out.add(call[1])
    return out


def leads(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Opening leads made by `name`."""
    ph = player_hands(df, name)
    rows = []
    for _, r in ph.iterrows():
        if r["contract"] == "PASS" or not isinstance(r["opening_lead"], str):
            continue
        if LEFT_OF[r["declarer"]] != r["seat"]:
            continue
        hand = r[f"hand_{r['seat']}"]
        info = classify_lead(
            hand,
            r["opening_lead"],
            r["strain"],
            defensive_suits(r["auction"], r["dealer"], r["seat"]),
        )
        info.update(hand_id=r["hand_id"], contract=r["contract"])
        rows.append(info)
    return pd.DataFrame(rows)


def result_patterns(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Made% and average score by role and strain."""
    ph = player_hands(df, name)
    ph = ph[(ph["contract"] != "PASS") & ph["tricks"].notna()].copy()
    ph["role"] = "defender"
    ph.loc[ph["is_declarer"], "role"] = "declarer"
    ph.loc[ph["is_dummy"], "role"] = "dummy"
    ph["made"] = ph["tricks"] >= ph["level"] + 6
    ph["declaring_side_score"] = ph["my_score"].where(ph["role"] != "defender", -ph["my_score"])
    g = ph.groupby(["role", "strain"])
    out = g.agg(
        n=("hand_id", "count"),
        made_pct=("made", lambda s: round(100 * s.mean(), 1)),
        avg_my_score=("my_score", "mean"),
    )
    out["avg_my_score"] = out["avg_my_score"].round(1)
    return out.reset_index()
