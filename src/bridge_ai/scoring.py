"""Duplicate bridge scoring."""

MINORS = "CD"
SEATS = "NESW"


def trick_value(strain: str) -> int:
    return 20 if strain in MINORS else 30


def score(level: int, strain: str, doubled: str, vulnerable: bool, tricks: int) -> int:
    """Score from declarer's side's point of view.

    strain is one of C D H S N; doubled is '', 'X' or 'XX'; tricks is tricks won by declarer.
    """
    mult = {"": 1, "X": 2, "XX": 4}[doubled]
    needed = level + 6
    if tricks < needed:
        down = needed - tricks
        if doubled == "":
            return -(100 if vulnerable else 50) * down
        if vulnerable:
            pen = 200 + 300 * (down - 1)
        else:
            pen = sum(100 if i == 1 else 200 if i < 4 else 300 for i in range(1, down + 1))
        return -pen * (mult // 2)
    over = tricks - needed
    if strain == "N":
        base = 40 + 30 * (level - 1)
    else:
        base = trick_value(strain) * level
    contract_pts = base * mult
    total = contract_pts
    if contract_pts >= 100:
        total += 500 if vulnerable else 300
    else:
        total += 50
    if level == 6:
        total += 750 if vulnerable else 500
    elif level == 7:
        total += 1500 if vulnerable else 1000
    total += {"": 0, "X": 50, "XX": 100}[doubled]
    if doubled == "":
        total += over * trick_value(strain)
    else:
        total += over * (100 if not vulnerable else 200) * (mult // 2)
    return total
