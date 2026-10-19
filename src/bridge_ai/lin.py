"""Parse BBO LIN hand records into structured deals."""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass, field

SEATS = "NESW"
DEALER_DIGIT = {"1": "S", "2": "W", "3": "N", "4": "E"}
VULNERABILITY = {"o": "None", "0": "None", "n": "NS", "e": "EW", "b": "Both"}
RANKS = "AKQJT98765432"
SUITS = "SHDC"
CALL_RE = re.compile(r"^(?:[1-7][CDHSN]|[pdr])$", re.IGNORECASE)


class LinError(ValueError):
    """Raised when a LIN string cannot be understood."""


@dataclass
class Contract:
    level: int
    strain: str
    doubled: str  # '', 'X' or 'XX'
    declarer: str  # N/E/S/W

    def __str__(self) -> str:
        return f"{self.level}{self.strain}{self.doubled}"


@dataclass
class Deal:
    board: int | None
    dealer: str
    vulnerability: str
    hands: dict[str, str]  # seat -> "S.H.D.C"
    players: dict[str, str]  # seat -> name ('' if unknown)
    auction: list[str]
    play: list[str]  # cards as 'HK', in play order
    claim: int | None = None  # tricks claimed (declarer's), if any
    alerts: int = 0
    alerted_calls: list[int] = field(default_factory=list)  # indices into auction
    contract: Contract | None = None
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def opening_lead(self) -> str | None:
        return self.play[0] if self.play else None

    @property
    def passed_out(self) -> bool:
        return bool(self.auction) and self.contract is None


def tokenize(lin: str) -> list[tuple[str, str]]:
    """Split 'tag|value|tag|value|' into pairs. Tolerates a trailing odd token."""
    parts = lin.split("|")
    if parts and parts[-1] == "":
        parts.pop()
    return [(parts[i], parts[i + 1] if i + 1 < len(parts) else "") for i in range(0, len(parts), 2)]


def parse_hand(text: str) -> str:
    """'SJ32HQ432DAT3CJT4' -> 'J32.Q432.AT3.JT4' (S.H.D.C, voids empty)."""
    m = re.fullmatch(r"S([^HDC]*)H([^DC]*)D([^C]*)C(.*)", text.upper())
    if not m:
        raise LinError(f"bad hand {text!r}")
    suits = [s.replace("10", "T") for s in m.groups()]
    for s in suits:
        if any(ch not in RANKS for ch in s):
            raise LinError(f"bad card in hand {text!r}")
    # LIN does not guarantee high-to-low order within a suit
    return ".".join("".join(sorted(s, key=RANKS.index)) for s in suits)


def _complete_hands(hands: dict[str, str]) -> dict[str, str]:
    """Infer a missing fourth hand from the other three."""
    missing = [s for s in SEATS if not hands.get(s)]
    if len(missing) != 1:
        return hands
    held = [set() for _ in range(4)]
    for h in hands.values():
        if h:
            for i, suit in enumerate(h.split(".")):
                held[i].update(suit)
    rest = ["".join(r for r in RANKS if r not in held[i]) for i in range(4)]
    hands = dict(hands)
    hands[missing[0]] = ".".join(rest)
    return hands


def contract_from_auction(auction: list[str], dealer: str) -> Contract | None:
    last = None
    doubled = ""
    first_bidder: dict[tuple[str, str], str] = {}
    for i, call in enumerate(auction):
        seat = SEATS[(SEATS.index(dealer) + i) % 4]
        c = call.upper()
        if c == "P":
            continue
        if c == "D":
            doubled = "X"
        elif c == "R":
            doubled = "XX"
        else:
            last = (int(c[0]), c[1], seat)
            doubled = ""
            side = "NS" if seat in "NS" else "EW"
            first_bidder.setdefault((side, c[1]), seat)
    if last is None:
        return None
    level, strain, seat = last
    side = "NS" if seat in "NS" else "EW"
    return Contract(level, strain, doubled, first_bidder[(side, strain)])


def parse_lin(lin: str) -> Deal:
    """Parse one LIN string (already URL-decoded)."""
    pairs = tokenize(lin)
    if not pairs:
        raise LinError("empty LIN")
    board = None
    dealer = None
    hands: dict[str, str] = {}
    players = dict.fromkeys(SEATS, "")
    vul = "None"
    auction: list[str] = []
    play: list[str] = []
    claim = None
    alerts = 0
    alerted_calls: list[int] = []
    extra: dict[str, str] = {}
    for tag, val in pairs:
        if tag == "md":
            if not val or val[0] not in DEALER_DIGIT:
                raise LinError(f"bad md {val!r}")
            dealer = DEALER_DIGIT[val[0]]
            parts = val[1:].split(",")
            if len(parts) < 3:
                raise LinError("fewer than three hands")
            for seat, text in zip("SWNE", parts, strict=False):
                if text:
                    hands[seat] = parse_hand(text)
        elif tag == "pn":
            names = val.split(",")
            for seat, name in zip("SWNE", names, strict=False):
                name = name.strip()
                players[seat] = "GiB" if name.startswith("~~") else name  # BBO robot
        elif tag == "ah":
            m = re.search(r"(\d+)", val)
            board = int(m.group(1)) if m else None
        elif tag == "sv":
            if val not in VULNERABILITY:
                raise LinError(f"bad vulnerability {val!r}")
            vul = VULNERABILITY[val]
        elif tag == "mb":
            call = val.rstrip("!")
            if not CALL_RE.match(call):
                raise LinError(f"bad call {val!r}")
            auction.append(call.upper())
            if val.endswith("!"):
                alerted_calls.append(len(auction) - 1)
        elif tag == "an":
            alerts += 1
            if auction and len(auction) - 1 not in alerted_calls:
                alerted_calls.append(len(auction) - 1)
        elif tag == "pc":
            card = val.upper()
            if len(card) != 2 or card[0] not in SUITS or card[1] not in RANKS:
                raise LinError(f"bad card {val!r}")
            play.append(card)
        elif tag == "mc":
            if val.isdigit():
                claim = int(val)
        else:
            extra[tag] = val
    if dealer is None:
        raise LinError("no md (deal) tag")
    hands = _complete_hands(hands)
    if len(hands) != 4 or any(not h for h in hands.values()):
        raise LinError("could not determine all four hands")
    for h in hands.values():
        if sum(len(s) for s in h.split(".")) != 13:
            raise LinError("hand does not contain 13 cards")
    deal = Deal(
        board=board,
        dealer=dealer,
        vulnerability=vul,
        hands=hands,
        players=players,
        auction=auction,
        play=play,
        claim=claim,
        alerts=alerts,
        alerted_calls=alerted_calls,
        extra=extra,
    )
    deal.contract = contract_from_auction(auction, dealer)
    return deal


def decode_lin(raw: str) -> str:
    """URL-decode a LIN as found in a link."""
    return urllib.parse.unquote(raw)
