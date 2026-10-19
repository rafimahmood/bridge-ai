import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "privacy_check", Path(__file__).parent.parent / "scripts" / "privacy_check.py"
)
pc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pc)

GOOD = """# Example hands

### 1. Demo

**A note.**

```
                  Partner
                  ♠ AKJ4
                  ♥ K109
LHO                                 RHO
♠ Q9                                ♠ —
                  Zia
                  ♠ 93
```

```
LHO       Partner   RHO       Zia
          1♣        X*        3NT
Pass      Pass      Pass
```

Dealer: Partner · Contract: 3NT by Zia made
"""


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(pc, "ROOT", tmp_path)
    (tmp_path / "docs" / "examples").mkdir(parents=True)
    return tmp_path


def write(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return rel


def test_curated_examples_are_allowed(root):
    f = write(root, "docs/examples/README.md", GOOD)
    assert pc.check_examples([f]) == []


def test_a_real_name_in_a_diagram_label_is_blocked(root):
    f = write(root, "docs/examples/README.md", GOOD.replace("Partner\n", "Mallory\n", 1))
    assert any("unexpected text" in p for p in pc.check_examples([f]))


def test_a_real_name_in_the_auction_header_is_blocked(root):
    f = write(
        root, "docs/examples/README.md", GOOD.replace("LHO       Partner", "Bob       Partner")
    )
    assert pc.check_examples([f])


def test_too_many_examples_blocked(root):
    f = write(root, "docs/examples/README.md", GOOD * 13)
    assert any("max" in p for p in pc.check_examples([f]))


def test_only_markdown_in_examples(root):
    f = write(root, "docs/examples/all.csv", "a,b")
    assert pc.check_examples([f])


@pytest.mark.parametrize(
    "path", ["data/x.html", ".cache/hands.parquet", "out/hands.csv", "a/b.pkl", ".env", "x.lin"]
)
def test_forbidden_paths(path):
    assert pc.check_paths([path])


def test_html_only_allowed_in_fixtures():
    assert pc.check_paths(["tests/fixtures/sample.html"]) == []
    assert pc.check_paths(["docs/page.html"])


def test_raw_lin_blocked_outside_tests(root):
    f = write(root, "docs/leak.md", "pn|Ann,Bob,Cy,Di|st||md|3SAKQ")
    assert pc.check_raw_lin([f])
    ok = write(root, "docs/ok.md", "Nothing here but prose.")
    assert pc.check_raw_lin([ok]) == []


def test_notebook_outputs_blocked(root):
    f = write(root, "nb.ipynb", '{"cells": [{"cell_type": "code", "outputs": [{"x": 1}]}]}')
    assert pc.check_notebooks([f])
    g = write(root, "ok.ipynb", '{"cells": [{"cell_type": "code", "outputs": []}]}')
    assert pc.check_notebooks([g]) == []


def test_name_scan_flags_other_players_but_not_the_allowed_one(root, monkeypatch):
    monkeypatch.setattr(pc, "player_names", lambda: {"mallory"})
    ok = write(root, "README.md", "Zia Mahmood plays on BBO.")
    bad = write(root, "NOTES.md", "Thanks to Mallory for the hands.")
    assert pc.check_names([ok], history=False) == []
    assert pc.check_names([bad], history=False)
