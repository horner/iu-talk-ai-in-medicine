#!/usr/bin/env python3
"""
05_visualize.py — Generate publication-quality charts from the processed trial data.

Charts (saved to output/charts/):
  1. trials_per_year.png — bar chart, most recent year highlighted
  2. phase_distribution.png — horizontal bar chart
  3. phase_by_year.png — stacked bar chart
  4. drug_class_distribution.png — horizontal bar chart
  5. condition_wheel.png — donut chart of top 15 conditions
  6. status_distribution.png — pie chart
  7. sponsor_types.png — bar chart
"""

import csv
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
CHART_DIR = os.path.join(SCRIPT_DIR, "output", "charts")

# ── Dependencies ─────────────────────────────────────────────────────────────
try:
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
except ImportError:
    sys.exit("ERROR: matplotlib is required.  pip install matplotlib")

try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False
    print("WARNING: seaborn not installed — using default matplotlib styles.")

# ── Style ────────────────────────────────────────────────────────────────────
if HAS_SEABORN:
    sns.set_theme(style="whitegrid", font_scale=1.1)
else:
    plt.rcParams.update({
        "axes.grid": True,
        "grid.alpha": 0.3,
        "figure.facecolor": "white",
    })

ACCENT = "#2563eb"       # blue
HIGHLIGHT = "#ef4444"    # red for latest year
PALETTE = [
    "#2563eb", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
    "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#6366f1",
    "#14b8a6", "#e11d48", "#a855f7", "#0ea5e9", "#eab308",
]


def read_csv(path):
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_fig(fig, name):
    path = os.path.join(CHART_DIR, name)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved {path}")


# ═══════════════════════════════════════════════════════════════════════════════
# Chart 1: Trials per year
# ═══════════════════════════════════════════════════════════════════════════════
def chart_trials_per_year(rows):
    year_counts = {}
    for r in rows:
        y = r.get("posted_year", "")
        if y and y.isdigit():
            yi = int(y)
            if 1990 <= yi <= 2030:
                year_counts[yi] = year_counts.get(yi, 0) + 1

    if not year_counts:
        print("  SKIP trials_per_year — no year data")
        return

    years = sorted(year_counts)
    counts = [year_counts[y] for y in years]
    max_year = max(years)

    fig, ax = plt.subplots(figsize=(12, 5))
    colors = [HIGHLIGHT if y == max_year else ACCENT for y in years]
    ax.bar(years, counts, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_xlabel("Year First Posted")
    ax.set_ylabel("Number of Trials")
    ax.set_title("GLP-1 Clinical Trials Posted Per Year", fontweight="bold", fontsize=14)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    # Annotate latest year
    ax.annotate(
        f"{year_counts[max_year]}",
        xy=(max_year, year_counts[max_year]),
        ha="center", va="bottom", fontweight="bold", fontsize=11, color=HIGHLIGHT,
    )
    save_fig(fig, "trials_per_year.png")


# ═══════════════════════════════════════════════════════════════════════════════
# Chart 2: Phase distribution
# ═══════════════════════════════════════════════════════════════════════════════
# Phases to exclude from phase-specific charts (non-drug / unspecified)
PHASE_EXCLUDE = {"NA", "Not Specified", ""}


def chart_phase_distribution(rows):
    phase_counts = {}
    excluded = 0
    for r in rows:
        p = r.get("phase", "").strip()
        if p in PHASE_EXCLUDE or not p:
            excluded += 1
            continue
        # Normalize "PHASE1|PHASE2" → "Phase 1/Phase 2"
        p = p.replace("EARLY_PHASE", "Early Phase ").replace("PHASE", "Phase ").replace("|", " / ").strip()
        phase_counts[p] = phase_counts.get(p, 0) + 1

    if not phase_counts:
        print("  SKIP phase_distribution — no data")
        return

    # Sort by phase number roughly
    def sort_key(p):
        if "Early" in p:
            return 0.5
        if "1" in p and "2" not in p:
            return 1
        if "1" in p and "2" in p:
            return 1.5
        if "2" in p and "3" not in p:
            return 2
        if "2" in p and "3" in p:
            return 2.5
        if "3" in p and "4" not in p:
            return 3
        if "4" in p:
            return 4
        return 6

    phases = sorted(phase_counts.keys(), key=sort_key)
    counts = [phase_counts[p] for p in phases]
    shown = sum(counts)

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.barh(phases, counts, color=ACCENT, edgecolor="white")
    ax.set_xlabel("Number of Trials")
    ax.set_title(f"Phase Distribution  ({shown:,} trials with a defined phase; {excluded:,} excluded)",
                 fontweight="bold", fontsize=12)
    ax.invert_yaxis()

    for bar, c in zip(bars, counts):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                str(c), va="center", fontsize=10)
    save_fig(fig, "phase_distribution.png")


# ═══════════════════════════════════════════════════════════════════════════════
# Chart 3: Phase by year (stacked)
# ═══════════════════════════════════════════════════════════════════════════════
def chart_phase_by_year(rows):
    # Build year → phase → count (excluding NA / Not Specified)
    data = {}
    all_phases = set()
    for r in rows:
        y = r.get("posted_year", "")
        if not y or not y.isdigit():
            continue
        yi = int(y)
        if yi < 2000 or yi > 2030:
            continue
        p = r.get("phase", "").strip()
        if p in PHASE_EXCLUDE or not p:
            continue
        p = p.replace("EARLY_PHASE", "Early Phase ").replace("PHASE", "Phase ").replace("|", " / ").strip()
        all_phases.add(p)
        data.setdefault(yi, {})
        data[yi][p] = data[yi].get(p, 0) + 1

    if not data:
        print("  SKIP phase_by_year — no data")
        return

    years = sorted(data)
    phase_list = sorted(all_phases)

    fig, ax = plt.subplots(figsize=(14, 6))
    bottom = [0] * len(years)
    for i, phase in enumerate(phase_list):
        vals = [data[y].get(phase, 0) for y in years]
        color = PALETTE[i % len(PALETTE)]
        ax.bar(years, vals, bottom=bottom, label=phase, color=color, edgecolor="white", linewidth=0.3)
        bottom = [b + v for b, v in zip(bottom, vals)]

    ax.set_xlabel("Year First Posted")
    ax.set_ylabel("Number of Trials")
    ax.set_title("GLP-1 Trials by Phase and Year (defined phases only)", fontweight="bold", fontsize=13)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    save_fig(fig, "phase_by_year.png")


# ═══════════════════════════════════════════════════════════════════════════════
# Chart 4: Drug class distribution
# ═══════════════════════════════════════════════════════════════════════════════
def chart_drug_class(rows):
    counts = {}
    for r in rows:
        m = r.get("mechanism_class", "Other/Unknown")
        counts[m] = counts.get(m, 0) + 1

    if not counts:
        print("  SKIP drug_class_distribution — no data")
        return

    classes = sorted(counts.keys(), key=lambda x: -counts[x])
    vals = [counts[c] for c in classes]

    fig, ax = plt.subplots(figsize=(9, 5))
    colors = PALETTE[:len(classes)]
    bars = ax.barh(classes, vals, color=colors, edgecolor="white")
    ax.set_xlabel("Number of Trials")
    ax.set_title("Trials by Drug Mechanism Class", fontweight="bold", fontsize=14)
    ax.invert_yaxis()

    for bar, v in zip(bars, vals):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                str(v), va="center", fontsize=10)
    save_fig(fig, "drug_class_distribution.png")


# ═══════════════════════════════════════════════════════════════════════════════
# Chart 5: Condition wheel (donut chart, top 15)
# ═══════════════════════════════════════════════════════════════════════════════
def chart_condition_wheel(condition_summary):
    # Top 15 + "Other"
    top_n = 15
    top = condition_summary[:top_n]
    rest_count = sum(int(r["trial_count"]) for r in condition_summary[top_n:])

    labels = [r["condition_normalized"] for r in top]
    sizes = [int(r["trial_count"]) for r in top]
    if rest_count > 0:
        labels.append("Other conditions")
        sizes.append(rest_count)

    if not sizes:
        print("  SKIP condition_wheel — no data")
        return

    colors = PALETTE * (len(labels) // len(PALETTE) + 1)
    fig, ax = plt.subplots(figsize=(9, 9))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=None, autopct=lambda p: f"{p:.1f}%" if p > 3 else "",
        colors=colors[:len(labels)], startangle=90,
        pctdistance=0.82, wedgeprops=dict(width=0.45, edgecolor="white", linewidth=1.5),
    )
    for at in autotexts:
        at.set_fontsize(8)

    ax.legend(
        wedges, [f"{l} ({s})" for l, s in zip(labels, sizes)],
        loc="center left", bbox_to_anchor=(1.05, 0.5), fontsize=9,
    )
    ax.set_title("Top Conditions in GLP-1 Trials", fontweight="bold", fontsize=14, y=1.02)
    save_fig(fig, "condition_wheel.png")


# ═══════════════════════════════════════════════════════════════════════════════
# Chart 6: Status distribution
# ═══════════════════════════════════════════════════════════════════════════════
def chart_status(rows):
    counts = {}
    for r in rows:
        s = r.get("status", "Unknown")
        counts[s] = counts.get(s, 0) + 1

    if not counts:
        print("  SKIP status_distribution — no data")
        return

    # Sort: Recruiting / Active first
    priority = ["RECRUITING", "ACTIVE_NOT_RECRUITING", "COMPLETED",
                "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION",
                "TERMINATED", "WITHDRAWN", "SUSPENDED", "UNKNOWN_STATUS"]
    ordered = sorted(counts.keys(), key=lambda s: (
        priority.index(s) if s in priority else 99
    ))
    vals = [counts[s] for s in ordered]
    labels = [s.replace("_", " ").title() for s in ordered]

    fig, ax = plt.subplots(figsize=(8, 8))
    colors = PALETTE[:len(labels)]
    wedges, texts, autotexts = ax.pie(
        vals, labels=None, autopct=lambda p: f"{p:.1f}%" if p > 2 else "",
        colors=colors, startangle=140, pctdistance=0.85,
    )
    for at in autotexts:
        at.set_fontsize(8)

    ax.legend(wedges, [f"{l} ({v})" for l, v in zip(labels, vals)],
              loc="center left", bbox_to_anchor=(1.05, 0.5), fontsize=9)
    ax.set_title("Trial Status Distribution", fontweight="bold", fontsize=14)
    save_fig(fig, "status_distribution.png")


# ═══════════════════════════════════════════════════════════════════════════════
# Chart 7: Sponsor types
# ═══════════════════════════════════════════════════════════════════════════════
def chart_sponsor_types(rows):
    counts = {}
    for r in rows:
        sc = r.get("sponsor_class", "Unknown")
        if not sc:
            sc = "Unknown"
        # Normalize casing
        sc = sc.replace("_", " ").title()
        counts[sc] = counts.get(sc, 0) + 1

    if not counts:
        print("  SKIP sponsor_types — no data")
        return

    labels = sorted(counts.keys(), key=lambda x: -counts[x])
    vals = [counts[l] for l in labels]

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = PALETTE[:len(labels)]
    bars = ax.bar(labels, vals, color=colors, edgecolor="white")
    ax.set_ylabel("Number of Trials")
    ax.set_title("Trials by Sponsor Type", fontweight="bold", fontsize=14)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                str(v), ha="center", va="bottom", fontsize=10, fontweight="bold")
    save_fig(fig, "sponsor_types.png")


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    os.makedirs(CHART_DIR, exist_ok=True)

    # Load classified trials
    classified_path = os.path.join(DATA_DIR, "classified_trials.csv")
    if not os.path.exists(classified_path):
        sys.exit(f"ERROR: {classified_path} not found. Run 03_classify_mechanisms.py first.")
    trials = read_csv(classified_path)
    print(f"Loaded {len(trials)} classified trials")

    # Load condition summary
    cond_summary_path = os.path.join(DATA_DIR, "condition_summary.csv")
    if not os.path.exists(cond_summary_path):
        sys.exit(f"ERROR: {cond_summary_path} not found. Run 04_analyze_conditions.py first.")
    condition_summary = read_csv(cond_summary_path)

    print(f"\nGenerating charts...")
    chart_trials_per_year(trials)
    chart_phase_distribution(trials)
    chart_phase_by_year(trials)
    chart_drug_class(trials)
    chart_condition_wheel(condition_summary)
    chart_status(trials)
    chart_sponsor_types(trials)
    print(f"\nDone — {len(os.listdir(CHART_DIR))} charts saved to {CHART_DIR}")


if __name__ == "__main__":
    main()
