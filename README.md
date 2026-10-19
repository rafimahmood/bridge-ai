# bridge-ai

**Goal: build an AI that can beat my dad at bridge.**

My dad plays a lot of online bridge on [Bridge Base Online](https://www.bridgebase.com) (BBO).
Beating someone consistently means knowing how they play, not just how to play well. So step
one is data: every hand BBO saves under "My hands" contains a full LIN record (deal, auction,
play, result). `bridge-ai` turns those saved pages into a clean table, profiles a player's
habits, and measures them against double-dummy perfection. Step two (the roadmap below) is an
opponent model that predicts what he will do, and a bot that exploits it.

## What it does

- **Parses** saved BBO "My hands" HTML pages: extracts the LIN of every hand, de-duplicates,
  tolerates broken files, and produces one row per deal (board, dealer, vulnerability, four
  hands, players, auction, opening lead, play, contract, declarer, tricks, score).
  Computed scores are checked against BBO's own score column.
- **Profiles a player**: opening bid frequencies by seat and vulnerability, likely psychs (bids
  that do not fit the hand's points or shape), opening lead choices, contract and result
  patterns.
- **Benchmarks** against [`endplay`](https://github.com/dominicprice/endplay) double-dummy
  solving: the player's actual tricks and scores versus double-dummy and par, converted to IMPs.

## Install and run

```bash
uv sync
uv run bridge-ai import data/            # folder of saved "My hands" .html pages
uv run bridge-ai players                 # most frequent players in the data
uv run bridge-ai stats --player <name>   # summary for one player
uv run bridge-ai benchmark --player <name>
```

For charts, run the notebook with `BRIDGE_PLAYER=<name> uv run jupyter lab notebooks/analysis.ipynb`.

To get data: on BBO open *My hands*, choose a date range, and save each page as HTML into
`data/`.

## Architecture

```
saved HTML  ->  html_extract  ->  lin  ->  dataset  ->  stats / analysis / ddbench  ->  CLI, notebook
              (rows + LIN)     (deal,    (table,        (profiles, psychs, leads,
                                auction,  dedupe,         double-dummy vs actual)
                                contract) scoring)
```

| Module | Role |
| --- | --- |
| `html_extract.py` | Pull table fields and URL-encoded LIN out of the saved pages |
| `lin.py` | Parse LIN into a `Deal` (hands, auction, play, contract, declarer) |
| `scoring.py` | Duplicate scoring |
| `dataset.py` | Build and de-duplicate the hands DataFrame, with an import report |
| `stats.py`, `analysis.py` | Per-player summaries, openings, psych flags, leads |
| `ddbench.py` | Double-dummy tables, par, IMPs against the actual result |
| `cli.py` | `bridge-ai` command |

## Privacy

Hand histories identify real people. The repository never contains them:

- `data/` and every derived file (CSV, parquet, cache) are in `.gitignore`.
- Tests use a small invented fixture (`tests/fixtures`) with made-up names.
- Notebook outputs are stripped on commit (`nbstripout`), and CI runs
  `scripts/privacy_check.sh` to fail on tracked data files or notebook outputs.

## Development

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

CI runs the same on every push.

## Roadmap

1. **Opponent model (next).** Learn a model of the target player from his hands: a bidding
   model (P(call | hand, auction, seat, vulnerability)), a lead model, and a declarer-play
   model, so the system can predict his actions and infer his likely holdings.
2. **Better psych and convention detection.** Use alert text and partnership history so
   artificial bids are not mistaken for psychs.
3. **Exploitative play.** Combine the opponent model with double-dummy sampling (determinisation
   over hands consistent with his bidding) to choose lines that beat his tendencies.
4. **Self-play evaluation.** Match the bot against him and baseline bots on fixed boards;
   report IMPs per board.
