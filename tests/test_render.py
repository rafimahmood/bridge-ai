from pathlib import Path

import pytest

from bridge_ai.dataset import build_dataset
from bridge_ai.render import (
    auction_table,
    call_text,
    contract_text,
    diagram,
    example_markdown,
    hand_lines,
    lead_text,
    seat_labels,
    vulnerability_text,
)
from bridge_ai.stats import player_hands

SAMPLE = Path(__file__).parent / "fixtures" / "sample_myhands.html"


@pytest.fixture
def carol():
    df, _ = build_dataset([SAMPLE])
    return player_hands(df, "carol")  # Carol sits North in the fixture


def test_seat_labels_rotate_around_the_hero():
    assert seat_labels("S") == {"S": "Zia", "W": "LHO", "N": "Partner", "E": "RHO"}
    assert seat_labels("N") == {"N": "Zia", "E": "LHO", "S": "Partner", "W": "RHO"}


def test_hand_lines_show_voids_and_tens():
    assert hand_lines("AT.K..QJ98") == ["♠ A10", "♥ K", "♦ —", "♣ QJ98"]


def test_call_text():
    assert call_text("1S") == "1♠"
    assert call_text("3N") == "3NT"
    assert call_text("P") == "Pass"
    assert call_text("D", alerted=True) == "X*"


def test_diagram_never_contains_player_names(carol):
    text = diagram(carol.iloc[0], "N")
    for name in ("Alice", "Bob", "Carol", "Dave"):
        assert name not in text
    assert "Partner" in text and "LHO" in text and "RHO" in text and "Zia" in text


def test_diagram_hero_hand_is_at_the_bottom(carol):
    row = carol.iloc[0]
    lines = diagram(row, "N").splitlines()
    assert lines[-4].strip().startswith("♠ " + row["hand_N"].split(".")[0])


def test_auction_starts_under_the_dealer(carol):
    row = carol.iloc[0]  # dealer North = Zia: first call is in the last column
    lines = auction_table(row, "N").splitlines()
    assert lines[0].split() == ["LHO", "Partner", "RHO", "Zia"]
    assert lines[1].index("1♠") == 30  # three empty columns of width 10, then Zia's call


def test_contract_and_lead_text(carol):
    row = carol.iloc[0]
    assert contract_text(row, "N") == "4♠ by Zia made"
    assert lead_text(row, "N") == "LHO led ♥J"
    assert contract_text(carol.iloc[1], "N") == "Passed out"
    assert lead_text(carol.iloc[1], "N") is None
    assert contract_text(carol.iloc[2], "N") == "3NTX by Zia down 2"


@pytest.mark.parametrize(
    ("vul", "text"),
    [
        ("None", "neither side vulnerable"),
        ("Both", "both sides vulnerable"),
        ("NS", "Zia's side vulnerable only"),
        ("EW", "opponents vulnerable only"),
    ],
)
def test_vulnerability_text(vul, text):
    assert vulnerability_text(vul, "N") == text


def test_example_markdown_has_title_note_and_blocks(carol):
    md = example_markdown("1. Demo", "A note.", carol.iloc[0], "N")
    assert md.startswith("### 1. Demo") and "**A note.**" in md
    assert md.count("```") == 4
