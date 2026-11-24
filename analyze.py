"""
analyze.py
----------
Loads the tidy `date | mode | trips` patronage dataset and produces
four charts covering a general overview across all modes:

  1. monthly_trends.png     - stacked monthly trips by mode, 2019-2025
  2. mode_share_2025.png    - mode share (%) for the most recent full year
  3. covid_recovery.png     - each mode indexed to its 2019 daily average
  4. weekday_vs_weekend.png - average daily trips, weekday vs weekend, by mode

Run: python3 analyze.py
(expects data/sydney_transport_patronage_synthetic.csv, produced by
 generate_data.py; charts are written to charts/)
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "sydney_transport_patronage_synthetic.csv"
CHARTS_DIR = ROOT / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

MODE_COLORS = {
    "Train": "#1f4e8c",
    "Metro": "#00a19a",
    "Bus": "#e07b39",
    "Ferry": "#2e9e4f",
    "Light Rail": "#9b59b6",
}
MODE_ORDER = ["Train", "Metro", "Bus", "Ferry", "Light Rail"]

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#444444",
    "axes.grid": True,
    "grid.color": "#e0e0e0",
    "grid.linewidth": 0.6,
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
})


def millions_formatter(x, pos):
    return f"{x/1e6:.0f}M"


def adaptive_formatter(x, pos):
    if x >= 1e6:
        return f"{x/1e6:.1f}M"
    return f"{x/1e3:.0f}K"


def load_data(path=DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df["mode"] = pd.Categorical(df["mode"], categories=MODE_ORDER, ordered=True)
    return df


def chart_monthly_trends(df: pd.DataFrame):
    monthly = (
        df.assign(month=df["date"].dt.to_period("M").dt.to_timestamp())
        .groupby(["month", "mode"], observed=True)["trips"].sum()
        .unstack("mode")[MODE_ORDER]
    )

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.stackplot(
        monthly.index, [monthly[m] for m in MODE_ORDER],
        labels=MODE_ORDER, colors=[MODE_COLORS[m] for m in MODE_ORDER],
        alpha=0.9,
    )
    ax.axvspan(pd.Timestamp("2020-03-01"), pd.Timestamp("2021-10-01"),
               color="grey", alpha=0.15, zorder=0)
    ax.text(pd.Timestamp("2020-06-15"), ax.get_ylim()[1] * 0.18,
            "COVID-19\nlockdowns", fontsize=9, color="#555555", ha="center")

    ax.set_title("Sydney public transport patronage by mode (monthly, illustrative)")
    ax.set_ylabel("Trips per month")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(millions_formatter))
    ax.legend(loc="upper left", ncol=5, frameon=False, fontsize=9,
              bbox_to_anchor=(0, 1.12))
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "monthly_trends.png", dpi=150)
    plt.close(fig)


def chart_mode_share(df: pd.DataFrame, year=2025):
    year_totals = (
        df[df["date"].dt.year == year]
        .groupby("mode", observed=True)["trips"].sum()
        .reindex(MODE_ORDER)
    )
    share = year_totals / year_totals.sum() * 100

    fig, ax = plt.subplots(figsize=(7, 6))
    wedges, _, autotexts = ax.pie(
        share, labels=None, autopct=lambda p: f"{p:.1f}%",
        colors=[MODE_COLORS[m] for m in MODE_ORDER],
        startangle=90, pctdistance=0.78,
        wedgeprops=dict(width=0.45, edgecolor="white", linewidth=2),
    )
    for t in autotexts:
        t.set_color("white")
        t.set_fontweight("bold")
        t.set_fontsize(10)

    ax.set_title(f"Mode share of trips, {year} (illustrative)")
    ax.legend(wedges, MODE_ORDER, loc="center left", bbox_to_anchor=(1, 0.5), frameon=False)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "mode_share_2025.png", dpi=150)
    plt.close(fig)


def chart_covid_recovery(df: pd.DataFrame):
    baseline = (
        df[df["date"].dt.year == 2019]
        .groupby("mode", observed=True)["trips"].mean()
    )
    monthly = (
        df.assign(month=df["date"].dt.to_period("M").dt.to_timestamp())
        .groupby(["month", "mode"], observed=True)["trips"].mean()
        .unstack("mode")[MODE_ORDER]
    )
    indexed = monthly.div(baseline, axis=1) * 100

    fig, ax = plt.subplots(figsize=(11, 6))
    for mode in MODE_ORDER:
        ax.plot(indexed.index, indexed[mode], label=mode,
                color=MODE_COLORS[mode], linewidth=2)
    ax.axhline(100, color="black", linewidth=1, linestyle="--", alpha=0.5)
    ax.text(indexed.index[3], 102, "2019 baseline (=100)", fontsize=9, color="#555555")

    ax.set_title("Recovery from COVID-19: patronage indexed to 2019 average (illustrative)")
    ax.set_ylabel("Index (2019 daily average = 100)")
    ax.legend(loc="upper left", frameon=False, ncol=5, fontsize=9)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "covid_recovery.png", dpi=150)
    plt.close(fig)


def chart_weekday_weekend(df: pd.DataFrame, year=2025):
    d = df[df["date"].dt.year == year].copy()
    d["day_type"] = d["date"].dt.dayofweek.apply(lambda x: "Weekend" if x >= 5 else "Weekday")
    avg = d.groupby(["mode", "day_type"], observed=True)["trips"].mean().unstack("day_type")
    avg = avg.reindex(MODE_ORDER)

    fig, ax = plt.subplots(figsize=(9, 6))
    x = range(len(MODE_ORDER))
    width = 0.35
    ax.bar([i - width/2 for i in x], avg["Weekday"], width, label="Weekday",
           color="#1f4e8c")
    ax.bar([i + width/2 for i in x], avg["Weekend"], width, label="Weekend",
           color="#e07b39")

    ax.set_xticks(list(x))
    ax.set_xticklabels(MODE_ORDER)
    ax.set_ylabel("Average trips per day")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(adaptive_formatter))
    ax.set_title(f"Average daily patronage: weekday vs weekend, {year} (illustrative)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "weekday_vs_weekend.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    df = load_data()
    chart_monthly_trends(df)
    chart_mode_share(df, year=2025)
    chart_covid_recovery(df)
    chart_weekday_weekend(df, year=2025)
    print(f"Saved 4 charts to {CHARTS_DIR}")
