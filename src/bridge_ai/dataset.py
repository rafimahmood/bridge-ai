"""Build a clean hands table from saved BBO pages."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .html_extract import RawRow, extract_file
from .lin import SEATS, Deal, LinError, parse_lin
from .scoring import score

log = logging.getLogger(__name__)

RESULT_RE = re.compile(r"^(\d)([CDHSN])(X{0,2})([NESW])(=|[+-]\d+)$", re.IGNORECASE)
COLUMNS = [
    "hand_id", "date", "time", "event_type", "board", "dealer", "vulnerability",
    "hand_N", "hand_E", "hand_S", "hand_W",
    "player_N", "player_E", "player_S", "player_W",
    "auction", "alerted_calls", "opening_lead", "play", "claim",
    "contract", "level", "strain", "doubled", "declarer",
    "tricks", "result", "ns_score", "table_score", "match_points", "source",
]  # fmt: skip


@dataclass
class ImportReport:
    files: int = 0
    rows: int = 0
    duplicates: int = 0
    bad_rows: int = 0
    bad_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _parse_result(text: str) -> tuple[int, str, str, str, int] | None:
    m = RESULT_RE.match(text.replace(" ", ""))
    if not m:
        return None
    level, strain, dbl, decl, delta = m.groups()
    delta_n = 0 if delta == "=" else int(delta)
    return int(level), strain.upper(), dbl.upper(), decl.upper(), int(level) + 6 + delta_n


def _is_vulnerable(vul: str, seat: str) -> bool:
    return vul == "Both" or (vul == "NS" and seat in "NS") or (vul == "EW" and seat in "EW")


def row_to_record(row: RawRow) -> dict:
    deal: Deal = parse_lin(row.lin)
    rec: dict = {
        "hand_id": row.hand_id or hashlib.sha1(row.lin.encode()).hexdigest()[:16],
        "date": row.date,
        "time": row.time,
        "event_type": row.event_type,
        "board": deal.board,
        "dealer": deal.dealer,
        "vulnerability": deal.vulnerability,
        "auction": " ".join(deal.auction),
        "alerted_calls": " ".join(map(str, deal.alerted_calls)),
        "opening_lead": deal.opening_lead,
        "play": " ".join(deal.play),
        "claim": deal.claim,
        "table_score": row.score,
        "match_points": row.match_points,
        "source": row.source,
    }
    for s in SEATS:
        rec[f"hand_{s}"] = deal.hands[s]
        rec[f"player_{s}"] = deal.players[s] or row.seats.get(s, "")
    c = deal.contract
    parsed = _parse_result(row.result_text)
    if c is None:
        rec.update(contract="PASS", ns_score=0, result="PASS")
        return rec
    rec.update(
        contract=str(c), level=c.level, strain=c.strain, doubled=c.doubled, declarer=c.declarer
    )
    if parsed and (parsed[0], parsed[1], parsed[3]) == (c.level, c.strain, c.declarer):
        tricks = parsed[4]
    elif parsed:
        raise LinError(f"result {row.result_text!r} disagrees with auction {c}")
    else:
        tricks = None
    rec["tricks"] = tricks
    if tricks is not None:
        diff = tricks - (c.level + 6)
        rec["result"] = "=" if diff == 0 else f"{diff:+d}"
        pts = score(
            c.level, c.strain, c.doubled, _is_vulnerable(deal.vulnerability, c.declarer), tricks
        )
        rec["ns_score"] = pts if c.declarer in "NS" else -pts
    return rec


def build_dataset(paths: list[Path]) -> tuple[pd.DataFrame, ImportReport]:
    report = ImportReport()
    records: dict[str, dict] = {}
    for path in paths:
        try:
            rows = extract_file(path)
        except Exception as exc:  # unreadable file: skip, keep going
            report.bad_files.append(f"{path.name}: {exc}")
            continue
        report.files += 1
        for row in rows:
            report.rows += 1
            try:
                rec = row_to_record(row)
            except LinError as exc:
                report.bad_rows += 1
                report.errors.append(f"{path.name}: {exc}")
                continue
            if rec["hand_id"] in records:
                report.duplicates += 1
                continue
            records[rec["hand_id"]] = rec
    df = pd.DataFrame(list(records.values()), columns=COLUMNS)
    return df, report


def find_pages(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in {".html", ".htm"})
