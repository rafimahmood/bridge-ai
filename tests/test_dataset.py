from pathlib import Path

import pytest

from bridge_ai.dataset import build_dataset, find_pages
from bridge_ai.html_extract import extract_file

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = FIXTURES / "sample_myhands.html"


def test_extract_rows_reads_table_fields():
    rows = extract_file(SAMPLE)
    assert len(rows) == 5
    first = rows[0]
    assert first.event_type == "mbc"
    assert first.date == "2026-01-05"
    assert first.time == "10:00"
    assert first.hand_id == "M-1-100"
    assert first.result_text == "4S" + "N="
    assert first.score == 420
    assert first.match_points == 2.0
    assert first.lin.startswith("pn|Alice,Dave,Carol,Bob|")  # URL-decoded


def test_build_dataset_dedupes_and_survives_bad_rows():
    df, report = build_dataset([SAMPLE])
    assert report.rows == 5
    assert report.duplicates == 1
    assert report.bad_rows == 1
    assert len(df) == 3
    assert list(df.hand_id) == ["M-1-100", "M-2-101", "M-3-102"]


def test_made_game_row():
    df, _ = build_dataset([SAMPLE])
    r = df.iloc[0]
    assert (r.contract, r.declarer, r.tricks, r.result) == ("4S", "N", 10, "=")
    assert r.ns_score == 420 == r.table_score
    assert r.opening_lead == "HK"
    assert r.player_N == "Carol" and r.player_S == "Alice"
    assert r.hand_N == "AKJ4.KT9.K76.J98"


def test_passed_out_row():
    df, _ = build_dataset([SAMPLE])
    r = df.iloc[1]
    assert r.contract == "PASS"
    assert r.ns_score == 0


def test_doubled_down_row_scores_for_ew():
    df, _ = build_dataset([SAMPLE])
    r = df.iloc[2]
    assert (r.contract, r.declarer, r.tricks, r.result) == ("3NX", "N", 7, "-2")
    assert r.vulnerability == "Both"
    assert r.ns_score == -500


def test_broken_and_empty_files_are_skipped(tmp_path):
    (tmp_path / "empty.html").write_text("")
    (tmp_path / "junk.html").write_bytes(b'\xff\xfe\x00garbage <tr class="mbc"> unclosed')
    (tmp_path / "notes.txt").write_text("not a page")
    (tmp_path / "good.html").write_text(SAMPLE.read_text())
    pages = find_pages(tmp_path)
    assert [p.name for p in pages] == ["empty.html", "good.html", "junk.html"]
    df, report = build_dataset(pages)
    assert len(df) == 3
    assert report.files == 3


def test_missing_file_is_reported_not_raised(tmp_path):
    df, report = build_dataset([tmp_path / "nope.html"])
    assert df.empty
    assert len(report.bad_files) == 1


def test_duplicates_across_files(tmp_path):
    (tmp_path / "a.html").write_text(SAMPLE.read_text())
    (tmp_path / "b.html").write_text(SAMPLE.read_text())
    df, report = build_dataset(find_pages(tmp_path))
    assert len(df) == 3
    assert report.duplicates == 5


@pytest.mark.parametrize("col", ["hand_N", "hand_E", "hand_S", "hand_W"])
def test_each_hand_has_13_cards(col):
    df, _ = build_dataset([SAMPLE])
    for h in df[col]:
        assert sum(len(s) for s in h.split(".")) == 13
