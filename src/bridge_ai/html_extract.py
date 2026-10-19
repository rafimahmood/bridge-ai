"""Extract hand rows (table fields + LIN) from saved BBO "My hands" pages."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

from .lin import decode_lin

ROW_RE = re.compile(r'<tr class="(mbc|team|tourney)">(.*?)</tr>', re.S)
DATE_RE = re.compile(r'<th colspan="\d+">(\d{4}-\d{2}-\d{2})</th>')
CELL_RE = re.compile(r'<td class="([^"]*)">(.*?)</td>', re.S)
LIN_RE = re.compile(r"hv_popuplin\('([^']*)'")
HAND_ID_RE = re.compile(r"myhand=(M-\d+-\d+)")
SUIT_ENTITY = {"spades": "S", "hearts": "H", "diamonds": "D", "diams": "D", "clubs": "C"}


@dataclass
class RawRow:
    source: str
    event_type: str  # mbc / team / tourney
    date: str | None
    time: str | None
    hand_id: str | None
    seats: dict[str, str]  # table-listed names by seat
    result_text: str
    score: int | None  # table score, viewer's perspective
    match_points: float | None  # IMPs / MPs column
    lin: str


def _text(cell: str) -> str:
    cell = re.sub(
        r"&(spades|hearts|diamonds|diams|clubs);", lambda m: SUIT_ENTITY[m.group(1)], cell
    )
    return html.unescape(re.sub(r"<[^>]+>", "", cell)).strip()


def _num(s: str) -> float | None:
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def extract_rows(text: str, source: str = "") -> list[RawRow]:
    """Return one RawRow per hand row that carries a LIN record."""
    rows = []
    # Track the most recent date header preceding each row.
    events = [(m.start(), "date", m.group(1)) for m in DATE_RE.finditer(text)]
    events += [(m.start(), "row", m) for m in ROW_RE.finditer(text)]
    date = None
    for _, kind, payload in sorted(events, key=lambda e: e[0]):
        if kind == "date":
            date = payload
            continue
        m = payload
        body = m.group(2)
        lin_m = LIN_RE.search(body)
        if not lin_m:
            continue
        cells = {}
        times = re.findall(r"<td>(\d{2}:\d{2})</td>", body)
        for cls, content in CELL_RE.findall(body):
            cells.setdefault(cls, _text(content))
        hid = HAND_ID_RE.search(body)
        scores = re.findall(r'<td class="(?:score|negscore)">(.*?)</td>', body, re.S)
        rows.append(
            RawRow(
                source=source,
                event_type=m.group(1),
                date=date,
                time=times[0] if times else None,
                hand_id=hid.group(1) if hid else None,
                seats={
                    "N": cells.get("north", ""),
                    "S": cells.get("south", ""),
                    "E": cells.get("east", ""),
                    "W": cells.get("west", ""),
                },
                result_text=cells.get("result", ""),
                score=int(v) if scores and (v := _num(_text(scores[0]))) is not None else None,
                match_points=_num(_text(scores[1])) if len(scores) > 1 else None,
                lin=decode_lin(html.unescape(lin_m.group(1))),
            )
        )
    return rows


def extract_file(path: Path) -> list[RawRow]:
    return extract_rows(path.read_text(encoding="utf-8", errors="replace"), source=path.name)
