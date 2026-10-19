"""Render a hand as a readable text diagram with anonymised seat labels."""

from __future__ import annotations

import pandas as pd

SEATS = "NESW"
SYMBOL = {"S": "♠", "H": "♥", "D": "♦", "C": "♣", "N": "NT"}
CALL_TEXT = {"P": "Pass", "D": "X", "R": "XX"}
WIDTH = 18


def seat_labels(hero_seat: str, hero_name: str = "Zia") -> dict[str, str]:
    """Map compass seats to Zia / LHO / Partner / RHO relative to the hero."""
    i = SEATS.index(hero_seat)
    return {
        hero_seat: hero_name,
        SEATS[(i + 1) % 4]: "LHO",
        SEATS[(i + 2) % 4]: "Partner",
        SEATS[(i + 3) % 4]: "RHO",
    }


def hand_lines(hand: str) -> list[str]:
    return [
        f"{SYMBOL[s]} {cards.replace('T', '10') or '—'}"
        for s, cards in zip("SHDC", hand.split("."), strict=True)
    ]


def call_text(call: str, alerted: bool = False) -> str:
    text = CALL_TEXT.get(call) or f"{call[0]}{SYMBOL[call[1]]}"
    return text + ("*" if alerted else "")


def diagram(row: pd.Series, hero_seat: str, hero_name: str = "Zia") -> str:
    """Hero at the bottom, partner at the top, LHO on the left, RHO on the right."""
    lab = seat_labels(hero_seat, hero_name)
    pos = {v: k for k, v in lab.items()}  # label -> compass seat
    hands = {name: hand_lines(row[f"hand_{seat}"]) for name, seat in pos.items()}
    out = []

    def centred(name: str) -> None:
        out.append(" " * WIDTH + name)
        out.extend(" " * WIDTH + line for line in hands[name])

    centred("Partner")
    left, right = ["LHO", *hands["LHO"]], ["RHO", *hands["RHO"]]
    for lft, rgt in zip(left, right, strict=True):
        out.append(lft.ljust(2 * WIDTH) + rgt)
    centred(hero_name)
    return "\n".join(line.rstrip() for line in out)


def auction_table(row: pd.Series, hero_seat: str, hero_name: str = "Zia") -> str:
    lab = seat_labels(hero_seat, hero_name)
    cols = [lab[SEATS[(SEATS.index(hero_seat) + k) % 4]] for k in (1, 2, 3, 0)]  # LHO P RHO hero
    calls = row["auction"].split()
    alerted = {int(x) for x in str(row.get("alerted_calls", "")).split()}
    start = cols.index(lab[row["dealer"]])
    cells = [""] * start + [call_text(c, i in alerted) for i, c in enumerate(calls)]
    lines = ["".join(c.ljust(10) for c in cols).rstrip()]
    for k in range(0, len(cells), 4):
        lines.append("".join(c.ljust(10) for c in cells[k : k + 4]).rstrip())
    return "\n".join(lines)


def vulnerability_text(vulnerability: str, hero_seat: str, hero_name: str = "Zia") -> str:
    if vulnerability == "None":
        return "neither side vulnerable"
    if vulnerability == "Both":
        return "both sides vulnerable"
    ours = (vulnerability == "NS") == (hero_seat in "NS")
    return f"{hero_name}'s side vulnerable only" if ours else "opponents vulnerable only"


def contract_text(row: pd.Series, hero_seat: str, hero_name: str = "Zia") -> str:
    if row["contract"] == "PASS":
        return "Passed out"
    lab = seat_labels(hero_seat, hero_name)
    c = row["contract"]
    level, strain, dbl = c[0], c[1], c[2:]
    text = f"{level}{SYMBOL[strain]}{dbl} by {lab[row['declarer']]}"
    if pd.notna(row.get("tricks")):
        diff = int(row["tricks"]) - (int(level) + 6)
        text += " made" if diff == 0 else f" +{diff}" if diff > 0 else f" down {-diff}"
    return text


def lead_text(row: pd.Series, hero_seat: str, hero_name: str = "Zia") -> str | None:
    lead = row.get("opening_lead")
    if not isinstance(lead, str) or row["contract"] == "PASS":
        return None
    lab = seat_labels(hero_seat, hero_name)
    leader = SEATS[(SEATS.index(row["declarer"]) + 1) % 4]
    return f"{lab[leader]} led {SYMBOL[lead[0]]}{lead[1].replace('T', '10')}"


def example_markdown(
    title: str, note: str, row: pd.Series, hero_seat: str, hero_name: str = "Zia"
) -> str:
    lab = seat_labels(hero_seat, hero_name)
    facts = [
        f"Dealer: {lab[row['dealer']]}",
        vulnerability_text(row["vulnerability"], hero_seat, hero_name).capitalize(),
        f"Contract: {contract_text(row, hero_seat, hero_name)}",
    ]
    lead = lead_text(row, hero_seat, hero_name)
    if lead:
        facts.append(lead)
    return (
        f"### {title}\n\n**{note}**\n\n"
        f"```\n{diagram(row, hero_seat, hero_name)}\n```\n\n"
        f"```\n{auction_table(row, hero_seat, hero_name)}\n```\n\n" + " · ".join(facts) + "\n"
    )
