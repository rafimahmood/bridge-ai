"""Privacy guard: keep real hand data and other players' names out of the repo.

    python3 scripts/privacy_check.py                 # structural checks (CI, stdlib only)
    python3 scripts/privacy_check.py --names         # also scan for names in the local dataset
    python3 scripts/privacy_check.py --names --history   # ... and in all of git history

Allowed: the player's own name (ALLOWED_NAMES) and the curated, anonymised hands in
docs/examples/. Blocked: data/, derived dataset files, raw LIN records, notebook outputs,
other players' names, and more than MAX_EXAMPLES example hands.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWED_NAMES = {"zia", "zia mahmood"}  # the player this project is about
FIXTURE_NAMES = {"alice", "bob", "carol", "dave", "gib"}  # invented, used in tests
MAX_EXAMPLES = 12
EXAMPLES_DIR = "docs/examples/"

FORBIDDEN_PATH = re.compile(
    r"^(data/|\.cache/)|\.(csv|parquet|feather|pkl|sqlite|db|lin)$|(^|/)\.env"
)
RAW_LIN = re.compile(r"md\|[1-4]S|%7Cmd%7C[1-4]S|(^|[^a-z])pn\|[^|]+,[^|]+,")
SUITS = "♠♥♦♣"
DIAGRAM_TOKEN = re.compile(rf"Partner|LHO|RHO|Zia|[{SUITS}] [AKQJ0-9—]+")
AUCTION_TOKEN = re.compile(rf"Partner|LHO|RHO|Zia|Pass|XX|X|\d(?:NT|[{SUITS}])|\*")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, errors="replace")


def tracked() -> list[str]:
    return [p for p in git("ls-files").splitlines() if (ROOT / p).is_file()]


def check_paths(files: list[str]) -> list[str]:
    problems = []
    for p in files:
        if FORBIDDEN_PATH.search(p):
            problems.append(f"forbidden file tracked: {p}")
        elif re.search(r"\.(html|js)$", p) and not p.startswith("tests/fixtures/"):
            problems.append(f"html/js tracked outside tests/fixtures: {p}")
    return problems


def check_notebooks(files: list[str]) -> list[str]:
    problems = []
    for p in files:
        if p.endswith(".ipynb"):
            nb = json.loads((ROOT / p).read_text())
            if any(c.get("outputs") for c in nb.get("cells", [])):
                problems.append(f"notebook has outputs: {p}")
    return problems


def check_raw_lin(files: list[str]) -> list[str]:
    problems = []
    for p in files:
        if (
            p.startswith("tests/")
            or p.endswith((".lock", ".ipynb"))
            or p == "scripts/privacy_check.py"
        ):
            continue
        if RAW_LIN.search((ROOT / p).read_text(errors="ignore")):
            problems.append(f"raw LIN / hand record found in {p}")
    return problems


def code_blocks(text: str) -> list[str]:
    return re.findall(r"```\n(.*?)```", text, re.S)


def check_examples(files: list[str]) -> list[str]:
    problems = []
    pages = [p for p in files if p.startswith(EXAMPLES_DIR)]
    count = 0
    for p in pages:
        if not p.endswith(".md"):
            problems.append(f"only Markdown allowed in {EXAMPLES_DIR}: {p}")
            continue
        text = (ROOT / p).read_text()
        count += len(re.findall(r"^### ", text, re.M))
        for block in code_blocks(text):
            is_auction = block.lstrip().startswith("LHO") and "Zia" in block.splitlines()[0]
            token = (
                AUCTION_TOKEN
                if is_auction and "Partner" in block.splitlines()[0]
                else DIAGRAM_TOKEN
            )
            if is_auction and block.splitlines()[0].split() != ["LHO", "Partner", "RHO", "Zia"]:
                problems.append(f"{p}: auction header must be exactly LHO Partner RHO Zia")
            leftover = token.sub("", block).strip()
            if leftover:
                problems.append(f"{p}: unexpected text in diagram: {leftover[:40]!r}")
    if count > MAX_EXAMPLES:
        problems.append(f"{count} example hands in {EXAMPLES_DIR} (max {MAX_EXAMPLES})")
    return problems


def player_names() -> set[str]:
    import pandas as pd  # local-only dependency

    cache = ROOT / ".cache" / "hands.parquet"
    if not cache.exists():
        print("note: no local dataset; skipping name scan", file=sys.stderr)
        return set()
    df = pd.read_parquet(cache)
    names = set()
    for s in "NESW":
        names |= {n.lower() for n in df[f"player_{s}"].dropna() if len(n) >= 3}
    return names - ALLOWED_NAMES - FIXTURE_NAMES


def check_names(files: list[str], history: bool) -> list[str]:
    names = player_names()
    if not names:
        return []
    texts = {p: (ROOT / p).read_text(errors="ignore").lower() for p in files}
    if history:
        texts["<git history>"] = git("log", "-p", "--all", "--format=%an %ae%n%s%n%b").lower()
    problems = []
    for name in sorted(names):
        pat = re.compile(r"(?<![a-z0-9])" + re.escape(name) + r"(?![a-z0-9])")
        for where, text in texts.items():
            if pat.search(text):
                problems.append(f"a player name from the dataset appears in {where}")
                break
    return problems


def main() -> int:
    files = tracked()
    problems = check_paths(files) + check_notebooks(files) + check_raw_lin(files)
    problems += check_examples(files)
    if "--names" in sys.argv:
        problems += check_names(files, "--history" in sys.argv)
    for p in problems:
        print("FAIL:", p)
    print("privacy check", "FAILED" if problems else "ok")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
