"""Generate notebooks/analysis.ipynb (no outputs). Run: uv run python scripts/make_notebook.py"""

import nbformat as nbf

nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
nb.cells = [
    md(
        "# Player analysis\n\nSet the `BRIDGE_PLAYER` environment variable to a BBO username and "
        "run `bridge-ai import data/` first. Outputs contain real hands, so they are stripped "
        "before commit (nbstripout); never commit an executed copy."
    ),
    code(
        "import os\n\nimport matplotlib.pyplot as plt\nimport pandas as pd\n\n"
        "from bridge_ai import analysis as an\nfrom bridge_ai import ddbench as dd\n\n"
        "PLAYER = os.environ['BRIDGE_PLAYER']\n"
        "df = pd.read_parquet('../.cache/hands.parquet')\n"
        "len(df)"
    ),
    md("## Opening bids by seat and vulnerability"),
    code(
        "op = an.openings(df, PLAYER)\n"
        "top = op['call'].value_counts().head(8).index\n"
        "fig, axes = plt.subplots(1, 2, figsize=(13, 4))\n"
        "for ax, by in zip(axes, ['seat_no', 'vul'], strict=True):\n"
        "    an.opening_table(op, by).loc[top].plot.bar(ax=ax)\n"
        "    ax.set_title(f'Opening call share by {by}'); ax.set_ylabel('share of openings')\n"
        "plt.tight_layout()"
    ),
    md(
        "## Likely psychs\n\nOpenings that miss a lenient standard definition "
        "(HCP and suit length). 2D is never flagged because it is often artificial."
    ),
    code(
        "ps = an.psychs(op)\nprint(f'{len(ps)} flagged of {len(op)} openings')\n"
        "ps['anomaly'].str.replace(r'\\d+', '#', regex=True).value_counts().plot.barh()"
    ),
    md("## Opening leads"),
    code(
        "ld = an.leads(df, PLAYER)\n"
        "kinds = pd.crosstab(ld['kind'], ld['vs'], normalize='columns').round(2)\n"
        "kinds.plot.bar(figsize=(10, 4))\n"
        "ld.groupby('vs')[['is_trump', 'is_bid_by_defence']].mean().round(2)"
    ),
    md("## Contract and result patterns"),
    code(
        "rp = an.result_patterns(df, PLAYER)\n"
        "rp[rp.role == 'declarer'].set_index('strain')[['made_pct']].plot.bar(legend=False)\n"
        "plt.ylabel('% contracts made as declarer'); rp"
    ),
    md("## Double-dummy and par benchmark"),
    code("ddf = dd.add_double_dummy(df)\npb = dd.player_benchmark(ddf, PLAYER)\ndd.summary(pb)"),
    code(
        "fig, axes = plt.subplots(1, 2, figsize=(13, 4))\n"
        "pb[pb.is_declarer]['tricks_vs_dd'].value_counts().sort_index().plot.bar(ax=axes[0])\n"
        "axes[0].set_title('Declarer tricks vs double dummy')\n"
        "pb['imps_vs_par'].plot.hist(bins=30, ax=axes[1]); axes[1].set_title('IMPs vs par')\n"
        "plt.tight_layout()"
    ),
]
nbf.write(nb, "notebooks/analysis.ipynb")
