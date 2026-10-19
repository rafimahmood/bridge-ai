"""bridge-ai command line interface."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer

from .dataset import build_dataset, find_pages
from .ddbench import add_double_dummy, player_benchmark
from .ddbench import summary as dd_summary
from .stats import player_counts, summarise

app = typer.Typer(help="Analyse bridge hands from Bridge Base Online.", no_args_is_help=True)

CACHE = Path(".cache/hands.parquet")


def _load(dataset: Path) -> pd.DataFrame:
    if not dataset.exists():
        typer.echo(f"No dataset at {dataset}. Run `bridge-ai import data/` first.", err=True)
        raise typer.Exit(1)
    return pd.read_parquet(dataset)


@app.command("import")
def import_(
    folder: Path = typer.Argument(..., exists=True, file_okay=False, help="Folder of saved pages"),
    out: Path = typer.Option(CACHE, help="Where to write the local dataset (keep out of git)"),
) -> None:
    """Build a local dataset from saved BBO "My hands" HTML pages."""
    pages = find_pages(folder)
    df, report = build_dataset(pages)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    typer.echo(
        f"{report.files} files, {report.rows} hand rows -> {len(df)} unique hands "
        f"({report.duplicates} duplicates, {report.bad_rows} unreadable rows)."
    )
    for msg in report.bad_files + report.errors[:10]:
        typer.echo(f"  warning: {msg}", err=True)
    typer.echo(f"Wrote {out}")


@app.command()
def players(
    top: int = typer.Option(15, help="How many players to list"),
    dataset: Path = typer.Option(CACHE),
) -> None:
    """List the most frequent players in the dataset."""
    counts = player_counts(_load(dataset)).head(top)
    for rank, (name, n) in enumerate(counts.items(), 1):
        typer.echo(f"{rank:>3}. {name:<20} {n:>5} hands")


@app.command()
def stats(
    player: str = typer.Option(..., "--player", help="BBO username (case-insensitive)"),
    dataset: Path = typer.Option(CACHE),
) -> None:
    """Print a summary for one player."""
    s = summarise(_load(dataset), player)
    if not s:
        typer.echo(f"No hands found for {player!r}.", err=True)
        raise typer.Exit(1)
    typer.echo(f"Player: {player}")
    typer.echo(f"Hands: {s['hands']}  ({s['first_date']} to {s['last_date']})")
    typer.echo(f"Seats: {s['by_seat']}   Events: {s['by_event']}")
    typer.echo(f"Passed out: {s['passed_out']}")
    typer.echo(f"Declared: {s['declared']}  made {s['declared_made_pct']}%")
    typer.echo(f"Average score (own side): {s['avg_score']}")
    typer.echo(f"Top contracts declared: {s['top_contracts_declared']}")
    typer.echo(f"Top partners: {s['partners']}")


@app.command()
def benchmark(
    player: str = typer.Option(..., "--player", help="BBO username (case-insensitive)"),
    dataset: Path = typer.Option(CACHE),
) -> None:
    """Compare a player's actual results with double-dummy results and par."""
    df = add_double_dummy(_load(dataset))
    pb = player_benchmark(df, player)
    if pb.empty:
        typer.echo(f"No scored hands for {player!r}.", err=True)
        raise typer.Exit(1)
    groups = [("All hands", pb)] + [(f"vs {k}", g) for k, g in pb.groupby("opponents")]
    for label, g in groups:
        s = dd_summary(g)
        typer.echo(f"\n{label}: {s['hands']} hands")
        typer.echo(f"  Average IMPs vs par: {s['avg_imps_vs_par']}")
        typer.echo(
            f"  Declarer: {s['declarer_tricks_vs_dd']} tricks vs double dummy on average; "
            f"matched or beat DD {s['declarer_beat_or_equal_dd_pct']}% of the time"
        )
        typer.echo(f"  Defence held declarer to DD or better: {s['defence_held_dd_pct']}%")
        typer.echo(f"  Matched par exactly: {s['par_matched_pct']}%")
