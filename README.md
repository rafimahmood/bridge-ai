# bridge-ai

**Goal: build an AI that can beat my dad at bridge.**

My dad is [Zia Mahmood](https://en.wikipedia.org/wiki/Zia_Mahmood), a 6-time world champion and
Bermuda Bowl winner. He plays a lot of online bridge on
[Bridge Base Online](https://www.bridgebase.com) (BBO), and his hands there are public records.
Beating someone consistently means knowing how they play, not just how to play well. So step one
is data: every hand BBO saves under "My hands" contains a full LIN record (deal, auction, play,
result). `bridge-ai` turns those saved pages into a clean table, profiles a player's habits, and
measures them against double-dummy perfection. Step two (see the roadmap) is an opponent model
that predicts what he will do, and a bot that exploits it.

The curated, anonymised [example hands](docs/examples/README.md) show what the analysis finds.
Everything else (the full dataset) stays on my machine; see [Privacy](#privacy).

## What it does

- **Parses** saved BBO "My hands" HTML pages: extracts the LIN of every hand, de-duplicates,
  tolerates broken files, and produces one row per deal (board, dealer, vulnerability, four
  hands, players, auction, opening lead, play, contract, declarer, tricks, score). Computed
  scores are checked against BBO's own score column.
- **Profiles a player**: opening bid frequencies by seat and vulnerability, likely psychs (bids
  that do not fit the hand's points or shape; alerted, i.e. artificial, calls are never
  flagged), opening lead choices, contract and result patterns.
- **Benchmarks** against [`endplay`](https://github.com/dominicprice/endplay) double-dummy
  solving: the player's actual tricks and scores versus double dummy and par, in IMPs, split
  by whether the opponents were humans or BBO robots.

## How to read the double-dummy numbers

Double dummy assumes all four hands are visible and every card is played perfectly. **No human
plays that way**, so the gap between a player's results and double dummy is a *baseline* to
reason against, not a criticism. Declarer can beat it when the defence goes wrong, and the
defence can beat it when declarer has to guess. What matters is the pattern: where the gap is
consistently positive or negative, and how it compares with other players.

For the 1,129 scored hands in my copy of his records, split by opposition because BBO robots
change the picture:

| Opponents | Hands | Declarer tricks vs double dummy (mean) | Avg IMPs vs par |
| --- | --- | --- | --- |
| Humans | 234 | 0.0 (66 hands as declarer; middle 80% within ±1 trick) | +0.3 |
| BBO robots | 895 | −1.6 (225 hands; median 0, but a long tail of large shortfalls) | −0.5 |

Read the robot row with care. Its mean is dragged down by a tail of very large shortfalls
(a few boards finish many tricks below double dummy), which could come from concessions,
abandoned boards or unusual partnership situations. I have not investigated them yet, so I
treat the human-opponent row as the cleaner baseline.

## Install and run

```bash
uv sync
uv run bridge-ai import data/            # folder of saved "My hands" .html pages
uv run bridge-ai players                 # most frequent players in the data
uv run bridge-ai stats --player <name>   # summary for one player
uv run bridge-ai benchmark --player <name>   # double dummy and par, split by opposition
```

For charts, run the notebook with `BRIDGE_PLAYER=<name> uv run jupyter lab notebooks/analysis.ipynb`.

Regenerate the example hands from the local dataset with
`uv run python scripts/make_examples.py --player <name> --name "Zia"`.

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
| `render.py` | Anonymised text diagrams of hands for the examples |
| `cli.py` | `bridge-ai` command |

## Privacy

Hand histories involve other real people, so only a small, curated slice is public:

- **Public:** the player's own name, and the handful of example hands in `docs/examples/`, where
  every other player is anonymised as Partner / LHO / RHO and dates, boards and hand IDs are
  removed.
- **Never committed:** `data/` and every derived file (CSV, parquet, cache) are gitignored, and
  other players' usernames appear nowhere in the repo. Tests use a small invented fixture
  (`tests/fixtures`) with made-up names. Notebook outputs are stripped on commit (`nbstripout`).
- **Enforced:** `scripts/privacy_check.py` runs in CI (no data files, no raw LIN, no notebook
  outputs, examples limited to anonymised labels and at most 12 hands). Locally it also scans
  all tracked files and git history for any player name found in the private dataset; enable it
  as a pre-push hook with `git config core.hooksPath .githooks`.

## Development

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
uv run python scripts/privacy_check.py --names --history   # needs the local dataset
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
