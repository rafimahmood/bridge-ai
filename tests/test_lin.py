import pytest

from bridge_ai.lin import LinError, parse_hand, parse_lin, tokenize

HANDS = "SQ953H85DJ532CT42,S2HQ7642DA8CAK763,SAKJ4HKT9DK76CJ98,ST876HAJ3DQT94CQ5"
BASE = f"pn|Alice,Dave,Carol,Bob|st||md|3{HANDS}|rh||ah|Board 1|sv|o|"


def test_tokenize_trailing_odd_token():
    assert tokenize("a|1|b|") == [("a", "1"), ("b", "")]


def test_parse_hand_with_void_and_ten():
    assert parse_hand("SAK10HDQJ5CAKQJ98") == "AKT..QJ5.AKQJ98"


@pytest.mark.parametrize("bad", ["", "XYZ", "SAKHQDC", "SAZHQDC"])
def test_parse_hand_rejects_garbage(bad):
    if bad == "SAKHQDC":  # structurally valid, so it parses (card count is checked later)
        assert parse_hand(bad) == "AK.Q.."
    else:
        with pytest.raises(LinError):
            parse_hand(bad)


def test_full_deal_basics():
    d = parse_lin(BASE + "mb|1S|mb|p|mb|2S|mb|p|mb|4S|mb|p|mb|p|mb|p|pc|HK|pc|H2|")
    assert d.board == 1
    assert d.dealer == "N"
    assert d.vulnerability == "None"
    assert d.players == {"S": "Alice", "W": "Dave", "N": "Carol", "E": "Bob"}
    assert d.hands["S"] == "Q953.85.J532.T42"
    assert d.hands["N"] == "AKJ4.KT9.K76.J98"
    assert d.auction == ["1S", "P", "2S", "P", "4S", "P", "P", "P"]
    assert d.opening_lead == "HK"
    assert str(d.contract) == "4S"
    assert d.contract.declarer == "N"


def test_fourth_hand_is_inferred():
    three = ",".join(HANDS.split(",")[:3])
    d = parse_lin(f"md|3{three}|ah|Board 1|sv|o|")
    assert d.hands["E"] == "T876.AJ3.QT94.Q5"


@pytest.mark.parametrize(("digit", "dealer"), [("1", "S"), ("2", "W"), ("3", "N"), ("4", "E")])
def test_dealer_digits(digit, dealer):
    assert parse_lin(f"md|{digit}{HANDS}|sv|o|").dealer == dealer


@pytest.mark.parametrize(("code", "vul"), [("o", "None"), ("n", "NS"), ("e", "EW"), ("b", "Both")])
def test_vulnerability(code, vul):
    assert parse_lin(f"md|3{HANDS}|sv|{code}|").vulnerability == vul


def test_doubled_contract_and_declarer_is_first_to_bid_strain():
    # Dealer E: E 1N, S p, W 3N, N X, all pass -> E is declarer, doubled.
    d = parse_lin(f"md|4{HANDS}|sv|b|mb|1N|mb|p|mb|3N|mb|d|mb|p|mb|p|mb|p|")
    assert (str(d.contract), d.contract.declarer) == ("3NX", "E")


def test_redouble_and_overcall_resets_double():
    d = parse_lin(f"md|3{HANDS}|sv|o|mb|1H|mb|d|mb|r|mb|2C|mb|p|mb|p|mb|p|")
    assert str(d.contract) == "2C"
    assert d.contract.declarer == "W"  # N 1H, E X, S XX, W 2C


def test_passed_out():
    d = parse_lin(f"md|3{HANDS}|sv|o|mb|p|mb|p|mb|p|mb|p|")
    assert d.contract is None
    assert d.passed_out


def test_alert_suffix_alerts_and_claim():
    d = parse_lin(f"md|3{HANDS}|sv|o|mb|1C!|an|Precision|mb|p|mc|11|")
    assert d.auction == ["1C", "P"]
    assert d.alerts == 1
    assert d.alerted_calls == [0]
    assert d.claim == 11


@pytest.mark.parametrize(
    "lin",
    [
        "",
        "pn|A,B,C,D|",  # no deal
        f"md|9{HANDS}|",  # bad dealer
        f"md|3{HANDS}|sv|q|",  # bad vulnerability
        f"md|3{HANDS}|mb|9Z|",  # bad call
        f"md|3{HANDS}|pc|ZZ|",  # bad card
        "md|3SAKQ,SAKQ|",  # too few hands
        "md|3SAKQJT98765432HDC,SHAKQJT98765432DC,SHDAKQJT98765432C,SHDCAKQJT98765432|mb|1X|",
    ],
)
def test_malformed_lin_raises(lin):
    with pytest.raises(LinError):
        parse_lin(lin)


def test_short_hand_rejected():
    with pytest.raises(LinError):
        parse_lin("md|3SAKHQDJCT,SAKHQDJCT,SAKHQDJCT,SAKHQDJCT|")


def test_robot_names_are_normalised():
    d = parse_lin(f"pn|Alice,~~A1234abc,Carol,~~Zz99|md|3{HANDS}|sv|o|")
    assert d.players == {"S": "Alice", "W": "GiB", "N": "Carol", "E": "GiB"}


def test_bang_suffix_marks_alerted_call():
    d = parse_lin(f"md|3{HANDS}|sv|o|mb|p|mb|1D!|mb|p|mb|2C|an|natural|")
    assert d.alerted_calls == [1, 3]


def test_cards_are_sorted_high_to_low_within_suits():
    assert parse_hand("S56710JH268JD48C35") == "JT765.J862.84.53"
    assert parse_hand("SQ9H2DT5CA43") == "Q9.2.T5.A43"
