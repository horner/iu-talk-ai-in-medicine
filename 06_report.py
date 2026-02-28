#!/usr/bin/env python3
"""
06_report.py — Generate a Markdown summary report from the processed data.

Reads the classified trials, condition summary, and QA report, then writes
output/report.md with:
  - Executive summary
  - Data quality section
  - Key breakdowns (tables)
  - Chart image references
  - Pistachio study mention
"""

import csv
import os
from collections import Counter
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
CHART_DIR = os.path.join(OUTPUT_DIR, "charts")


def read_csv(path):
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_text(path):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def md_table(headers, rows):
    """Build a Markdown table string."""
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── Load data ────────────────────────────────────────────────────────────
    classified_path = os.path.join(DATA_DIR, "classified_trials.csv")
    cond_summary_path = os.path.join(DATA_DIR, "condition_summary.csv")
    qa_path = os.path.join(DATA_DIR, "qa_report.txt")

    if not os.path.exists(classified_path):
        print(f"ERROR: {classified_path} not found. Run the pipeline first.")
        return

    trials = read_csv(classified_path)
    cond_summary = read_csv(cond_summary_path) if os.path.exists(cond_summary_path) else []
    qa_text = read_text(qa_path)

    total = len(trials)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ── Compute summaries ────────────────────────────────────────────────────
    status_counts = Counter(r.get("status", "Unknown") for r in trials)
    phase_counts = Counter(
        r.get("phase", "Not Specified").replace("EARLY_PHASE", "Early Phase ").replace("PHASE", "Phase ").replace("|", " / ").strip() or "Not Specified"
        for r in trials
    )
    mech_counts = Counter(r.get("mechanism_class", "Other/Unknown") for r in trials)
    therapy_counts = Counter(r.get("therapy_type", "Unknown") for r in trials)
    sponsor_counts = Counter(
        (r.get("sponsor_class", "Unknown") or "Unknown").replace("_", " ").title()
        for r in trials
    )

    # Year range
    years = [int(r["posted_year"]) for r in trials
             if r.get("posted_year", "").isdigit()]
    min_year = min(years) if years else "?"
    max_year = max(years) if years else "?"
    latest_year_count = years.count(max_year) if years else 0

    # Pistachio study
    pistachio = [r for r in trials if "pistachio" in (r.get("brief_title", "") + r.get("official_title", "")).lower()]

    # ── Build report ─────────────────────────────────────────────────────────
    report = []

    # Title
    report.append("# GLP-1 Clinical Trials Analysis Report")
    report.append(f"\n*Generated {now} — Data from ClinicalTrials.gov API v2*\n")

    # Executive summary
    report.append("## Executive Summary\n")
    report.append(f"This analysis covers **{total:,}** unique clinical trials related to GLP-1 "
                  f"receptor agonists and related therapies, posted between **{min_year}** and **{max_year}**.\n")
    # Find the actual peak completed year (exclude current partial year)
    from collections import Counter as YearCounter
    year_counter = YearCounter(years)
    current_year = datetime.now().year
    full_years = {y: c for y, c in year_counter.items() if y < current_year}
    peak_year = max(full_years, key=full_years.get) if full_years else max_year
    peak_count = full_years.get(peak_year, 0)

    if max_year == current_year:
        report.append(f"- **{latest_year_count}** trials already posted in {max_year} (year in progress)")
        report.append(f"- **{peak_count}** trials posted in {peak_year} — the highest completed year")
    else:
        report.append(f"- **{latest_year_count}** trials posted in {max_year} — the highest single year on record")
    active = sum(v for k, v in status_counts.items() if k in ("RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION"))
    completed = status_counts.get("COMPLETED", 0)
    report.append(f"- **{active}** trials currently active or recruiting")
    report.append(f"- **{completed}** trials completed")
    report.append(f"- **{len(mech_counts)}** distinct drug mechanism classes identified\n")

    # Data quality — show summary only, not every individual issue
    report.append("## Data Quality\n")
    if qa_text:
        # Parse key counts from the QA report
        import re as _re
        total_issues_m = _re.search(r"Total issues found:\s*(\d+)", qa_text)
        drug_cond_m = _re.search(r"Drug names listed as conditions:\s*(\d+)", qa_text)
        encoding_m = _re.search(r"Encoding issues fixed:\s*(\d+)", qa_text)
        empty_cond_m = _re.search(r"Empty conditions:\s*(\d+)", qa_text)
        empty_int_m = _re.search(r"Empty interventions:\s*(\d+)", qa_text)
        missing_phase_m = _re.search(r"Missing phase:\s*(\d+)", qa_text)
        missing_status_m = _re.search(r"Missing status:\s*(\d+)", qa_text)

        report.append("The cleaning step identified the following issues in the raw data:\n")
        report.append(md_table(
            ["Issue Category", "Count"],
            [
                ("Total issues", total_issues_m.group(1) if total_issues_m else "?"),
                ("Drug names listed as conditions", drug_cond_m.group(1) if drug_cond_m else "?"),
                ("Encoding issues fixed", encoding_m.group(1) if encoding_m else "?"),
                ("Empty conditions", empty_cond_m.group(1) if empty_cond_m else "?"),
                ("Empty interventions", empty_int_m.group(1) if empty_int_m else "?"),
                ("Missing phase", missing_phase_m.group(1) if missing_phase_m else "?"),
                ("Missing status", missing_status_m.group(1) if missing_status_m else "?"),
            ]
        ))
        report.append("\n*See `data/qa_report.txt` for full details.*\n")
    else:
        report.append("QA report not found — run `02_clean_data.py` to generate.\n")

    # Status breakdown
    report.append("## Trial Status\n")
    status_rows = sorted(status_counts.items(), key=lambda x: -x[1])
    report.append(md_table(
        ["Status", "Count", "% of Total"],
        [(s.replace("_", " ").title(), f"{c:,}", f"{c/total*100:.1f}%") for s, c in status_rows]
    ))
    report.append("")

    # Phase breakdown — exclude NA and Not Specified
    excluded_phases = {"NA", "Not Specified"}
    phase_rows_filtered = [(p, c) for p, c in phase_counts.items() if p not in excluded_phases]
    phase_rows_filtered.sort(key=lambda x: -x[1])
    excluded_count = sum(c for p, c in phase_counts.items() if p in excluded_phases)
    shown_count = sum(c for _, c in phase_rows_filtered)

    report.append("## Phase Distribution\n")
    report.append(f"*Showing {shown_count:,} trials with a defined phase. "
                  f"{excluded_count:,} trials excluded (NA = non-drug interventional, "
                  f"Not Specified = missing phase data).*\n")
    report.append(md_table(
        ["Phase", "Count", "% of Phased Trials"],
        [(p, f"{c:,}", f"{c/shown_count*100:.1f}%") for p, c in phase_rows_filtered]
    ))
    report.append("")

    # Mechanism classification
    report.append("## Drug Mechanism Classes\n")
    mech_rows = sorted(mech_counts.items(), key=lambda x: -x[1])
    report.append(md_table(
        ["Mechanism Class", "Count", "% of Total"],
        [(m, f"{c:,}", f"{c/total*100:.1f}%") for m, c in mech_rows]
    ))
    report.append("")

    # Therapy type
    report.append("## Therapy Type\n")
    therapy_rows = sorted(therapy_counts.items(), key=lambda x: -x[1])
    report.append(md_table(
        ["Therapy Type", "Count"],
        [(t, f"{c:,}") for t, c in therapy_rows]
    ))
    report.append("")

    # Sponsor types
    report.append("## Sponsor Types\n")
    sponsor_rows = sorted(sponsor_counts.items(), key=lambda x: -x[1])
    report.append(md_table(
        ["Sponsor Class", "Count"],
        [(s, f"{c:,}") for s, c in sponsor_rows]
    ))
    report.append("")

    # Top conditions
    report.append("## Top Conditions\n")
    if cond_summary:
        top20 = cond_summary[:20]
        report.append(md_table(
            ["Condition", "Broad Category", "Trial Count"],
            [(r["condition_normalized"], r["broad_category"], r["trial_count"])
             for r in top20]
        ))
    else:
        report.append("*Condition summary not available — run `04_analyze_conditions.py`.*\n")
    report.append("")

    # Charts
    report.append("## Charts\n")
    chart_files = [
        ("trials_per_year.png", "Trials Posted Per Year"),
        ("phase_distribution.png", "Phase Distribution"),
        ("phase_by_year.png", "Phase Distribution by Year"),
        ("drug_class_distribution.png", "Drug Mechanism Class Distribution"),
        ("condition_wheel.png", "Top Conditions (Donut Chart)"),
        ("status_distribution.png", "Trial Status Distribution"),
        ("sponsor_types.png", "Sponsor Types"),
    ]
    for fname, caption in chart_files:
        fpath = os.path.join(CHART_DIR, fname)
        if os.path.exists(fpath):
            report.append(f"### {caption}\n")
            report.append(f"![{caption}](charts/{fname})\n")
        else:
            report.append(f"### {caption}\n")
            report.append(f"*Chart not generated — run `05_visualize.py`.*\n")

    # Fun finding: Pistachio study
    report.append("## Notable Finding: The Pistachio Study\n")
    if pistachio:
        p = pistachio[0]
        report.append(f"Among all the GLP-1 clinical trials, one stood out:\n")
        report.append(f"> **{p.get('brief_title', '')}**\n>\n"
                      f"> NCT ID: {p.get('nct_id', '')} | Status: {p.get('status', '')} | "
                      f"Phase: {p.get('phase', 'N/A')}\n")
        report.append("As the video creator noted: participants will eat 53 grams "
                      "(¾ cup) of pistachios per day while on GLP-1 therapy.\n")
    else:
        report.append("The pistachio study mentioned in the original video was not found in "
                      "this dataset. It may be indexed under a different search term.\n")

    # Methodology
    report.append("## Methodology\n")
    report.append("1. **Data Fetch**: Queried ClinicalTrials.gov API v2 with 11 GLP-1-related "
                  "search terms, paginated, and deduplicated by NCT ID\n")
    report.append("2. **Cleaning**: Unicode normalization, condition splitting, drug-as-condition "
                  "flagging, year extraction\n")
    report.append("3. **Classification**: Mapped interventions to mechanism classes (GLP-1 RA, "
                  "GIP/GLP-1 Dual, Triple Agonist, etc.) and therapy types\n")
    report.append("4. **Condition Analysis**: Normalized condition variants, mapped to broad "
                  "therapeutic categories\n")
    report.append("5. **Visualization**: Generated 7 publication-quality charts\n")
    report.append("6. **Report**: This document\n")

    # Footer
    report.append("---\n")
    report.append(f"*Pipeline: `01_fetch_trials.py` → `02_clean_data.py` → "
                  f"`03_classify_mechanisms.py` → `04_analyze_conditions.py` → "
                  f"`05_visualize.py` → `06_report.py`*\n")

    # Write report
    report_path = os.path.join(OUTPUT_DIR, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    print(f"Report saved to {report_path}")
    print(f"  - {total:,} trials analyzed")
    print(f"  - {len(chart_files)} chart references included")


if __name__ == "__main__":
    main()
