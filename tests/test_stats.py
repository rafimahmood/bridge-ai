from pathlib import Path

from bridge_ai.dataset import build_dataset
from bridge_ai.stats import player_hands

SAMPLE = Path(__file__).parent / "fixtures" / "sample_myhands.html"


def test_opponents_flagged_robot_when_gib_sits_opposite_side(tmp_path):
    page = SAMPLE.read_text().replace("%2CBob%7C", "%2C~~X1234%7C")  # East becomes a robot
    (tmp_path / "p.html").write_text(page)
    df, _ = build_dataset([tmp_path / "p.html"])
    assert (df["player_E"] == "GiB").all()
    carol = player_hands(df, "carol")  # North: East is an opponent
    assert set(carol["opponents"]) == {"robots"}
    assert not carol["partner_is_robot"].any()
    alice = player_hands(df, "alice")  # South: East is an opponent too
    assert set(alice["opponents"]) == {"robots"}
    bob_side = player_hands(df, "dave")  # West: robot East is partner, not opponent
    assert set(bob_side["opponents"]) == {"humans"}
    assert bob_side["partner_is_robot"].all()
