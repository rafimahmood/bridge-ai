from pathlib import Path

import pytest

from bridge_ai.analysis import (
    classify_lead,
    defensive_suits,
    hcp,
    is_balanced,
    leads,
    opening_anomaly,
    opening_table,
    openings,
    psychs,
    relative_vul,
    result_patterns,
    shape,
)
from bridge_ai.dataset import build_dataset

SAMPLE = Path(__file__).parent / "fixtures" / "sample_myhands.html"
HAND = "AKJ4.KT9.K76.J98"  # 15 HCP, 4333


def test_hcp_shape_balanced():
    assert hcp(HAND) == 15
    assert shape(HAND) == (4, 3, 3, 3)
    assert is_balanced(HAND)
    assert not is_balanced("AKQJ98.AK.32.987")


@pytest.mark.parametrize(
    ("vul", "seat", "expected"),
    [
        ("None", "N", "NV/NV"),
        ("Both", "E", "Vul/Vul"),
        ("NS", "S", "Vul/NV"),
        ("NS", "W", "NV/Vul"),
        ("EW", "E", "Vul/NV"),
    ],
)
def test_relative_vul(vul, seat, expected):
    assert relative_vul(vul, seat) == expected


@pytest.mark.parametrize(
    ("hand", "call", "seat_no", "flagged"),
    [
        (HAND, "1N", 1, False),
        ("432.432.432.5432", "1N", 1, True),
        (HAND, "1S", 1, False),
        ("32.432.432.AKQJ9", "1S", 1, True),  # 2-card spade suit, 10 HCP
        ("AQ5.K43.J943.J72", "1C", 3, False),
        ("432.432.5432.432", "1D", 1, True),  # 0 HCP
        ("432.432.5432.432", "1D", 4, True),
        ("KQJ987.43.432.32", "2S", 1, False),
        ("AKQJ87.AK.432.32", "2S", 1, True),  # too strong for a weak two
        ("KQ98.432.432.432", "2H", 1, True),  # 3-card heart suit
        ("432.432.5432.432", "2D", 1, False),  # 2D never flagged (often artificial)
        ("32.32.32.KQJ9876", "3C", 1, False),
        ("AKQ.AKQ.AKQ.AKQ2", "3C", 1, True),
    ],
)
def test_opening_anomaly(hand, call, seat_no, flagged):
    assert (opening_anomaly(hand, call, seat_no) is not None) == flagged


@pytest.mark.parametrize(
    ("holding_hand", "card", "strain", "kind"),
    [
        ("AKJ4.KT9.K76.J98", "SA", "H", "top of sequence"),
        ("K5.QJT9.5432.432", "HQ", "N", "top of sequence"),
        ("5.QJT9.5432.K432", "S5", "N", "singleton"),
        ("A54.QJT9.5432.432", "SA", "N", "ace"),
        ("432.QJT9.K532.432", "D2", "N", "fourth best"),
        ("A32.QJT9.K32.432", "S2", "N", "low from three"),
        ("32.QJT9.K532.432", "S2", "N", "doubleton (low)"),
    ],
)
def test_classify_lead(holding_hand, card, strain, kind):
    got = classify_lead(holding_hand, card, strain, set())
    assert got["kind"] == kind


def test_classify_lead_flags():
    info = classify_lead(HAND, "SK", "S", {"S"})
    assert info["is_trump"] and info["is_bid_by_defence"] and info["vs"] == "suit"
    assert classify_lead(HAND, "SK", "N", set())["vs"] == "NT"


def test_defensive_suits():
    # Dealer N: N 1H, E 1S, S 2H, W 2S, then passes. Leader is N (E declares) -> N/S suits.
    assert defensive_suits("1H 1S 2H 2S P P P", "N", "N") == {"H"}
    assert defensive_suits("1H 1S 2H 2S P P P", "N", "E") == {"S"}
    assert defensive_suits("1N P 3N P P P", "N", "E") == set()


def test_openings_on_fixture():
    df, _ = build_dataset([SAMPLE])
    op = openings(df, "carol")  # North
    assert list(op["call"]) == ["1S", "1N"]
    assert list(op["seat_no"]) == [1, 2]
    assert list(op["vul"]) == ["NV/NV", "Vul/Vul"]
    table = opening_table(op)
    assert abs(table.sum().sum() - table.shape[1]) < 1e-9
    assert psychs(op).shape[0] <= len(op)


def test_leads_and_results_on_fixture():
    df, _ = build_dataset([SAMPLE])
    # Declarer is North (Carol), so East (Bob) is on lead.
    bob_leads = leads(df, "bob")
    assert bob_leads.iloc[0]["suit"] == "H"
    assert bob_leads.iloc[0]["rank"] == "J"
    patterns = result_patterns(df, "carol")
    assert set(patterns["role"]) == {"declarer"}
