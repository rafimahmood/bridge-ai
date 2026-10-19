import pytest

from bridge_ai.scoring import score


@pytest.mark.parametrize(
    ("level", "strain", "dbl", "vul", "tricks", "expected"),
    [
        (4, "S", "", False, 10, 420),
        (4, "H", "", True, 10, 620),
        (3, "N", "", False, 9, 400),
        (3, "N", "", True, 9, 600),
        (1, "N", "", False, 7, 90),
        (2, "S", "", False, 8, 110),
        (2, "C", "", False, 8, 90),
        (6, "S", "", False, 12, 980),
        (6, "N", "", True, 12, 1440),
        (7, "N", "", True, 13, 2220),
        (7, "S", "", False, 13, 1510),
        (4, "S", "", False, 11, 450),
        (3, "N", "X", True, 9, 750),
        (2, "H", "X", False, 8, 470),
        (1, "S", "XX", False, 7, 520),
        (4, "S", "", False, 9, -50),
        (4, "S", "", True, 8, -200),
        (3, "N", "X", True, 7, -500),
        (3, "N", "X", False, 6, -500),
        (4, "S", "X", False, 6, -800),
        (4, "S", "X", False, 5, -1100),
        (4, "S", "X", True, 8, -500),
        (4, "S", "XX", True, 8, -1000),
        (4, "S", "", False, 0, -500),
    ],
)
def test_score(level, strain, dbl, vul, tricks, expected):
    assert score(level, strain, dbl, vul, tricks) == expected
