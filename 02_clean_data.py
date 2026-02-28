#!/usr/bin/env python3
"""
02_clean_data.py — Clean the raw trial data.

- Normalize conditions (split multi-value strings)
- Flag drug names mistakenly listed as conditions
- Fix encoding / unicode issues
- Extract posted_year
- Generate a QA report
"""

import csv
import os
import re
import unicodedata

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

KNOWN_DRUGS = [
    "semaglutide", "liraglutide", "tirzepatide", "exenatide", "dulaglutide",
    "lixisenatide", "albiglutide", "survodutide", "cotadutide", "retatrutide",
    "orforglipron", "danuglipron", "efinopegdutide", "pemvidutide", "mazdutide",
    "cagrilintide", "insulin", "metformin", "empagliflozin", "dapagliflozin",
    "canagliflozin", "sitagliptin", "linagliptin", "saxagliptin", "ozempic",
    "wegovy", "mounjaro", "trulicity", "victoza", "byetta", "bydureon",
    "rybelsus", "saxenda",
]


def read_csv(path):
    """Read CSV into list of dicts."""
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_csv(rows, path):
    """Write list of dicts as CSV."""
    if not rows:
        return
    headers = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def normalize_text(text):
    """Unicode normalize + strip weird chars."""
    if not text:
        return ""
    # NFKD normalization
    text = unicodedata.normalize("NFKD", text)
    # Remove control characters
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_conditions(cond_str):
    """Split a pipe/comma/semicolon separated condition string into a list."""
    if not cond_str:
        return []
    # Already pipe-separated from fetch step; also handle raw delimiters
    parts = re.split(r"[|;]+", cond_str)
    result = []
    for p in parts:
        p = normalize_text(p)
        if p:
            result.append(p)
    return result


def is_drug_name(condition):
    """Check if a condition string is actually a drug name."""
    cond_lower = condition.lower().strip()
    for drug in KNOWN_DRUGS:
        if drug in cond_lower:
            return True
    return False


def extract_year(date_str):
    """Extract year from a date string like '2023-05-15' or '2023'."""
    if not date_str:
        return ""
    m = re.match(r"(\d{4})", str(date_str))
    return m.group(1) if m else ""


def main():
    input_path = os.path.join(DATA_DIR, "raw_trials.csv")
    if not os.path.exists(input_path):
        print(f"ERROR: {input_path} not found. Run 01_fetch_trials.py first.")
        return

    rows = read_csv(input_path)
    print(f"Loaded {len(rows)} rows from raw_trials.csv")

    qa_issues = {
        "drug_as_condition": [],
        "encoding_fixed": [],
        "empty_conditions": [],
        "empty_interventions": [],
        "missing_phase": [],
        "missing_status": [],
    }

    cleaned = []
    for row in rows:
        # Normalize text fields
        for key in row:
            original = row[key]
            row[key] = normalize_text(str(row[key])) if row[key] else ""
            if original and row[key] != original and key not in ("conditions", "intervention_names"):
                qa_issues["encoding_fixed"].append((row.get("nct_id", ""), key))

        # Split and check conditions
        conditions = split_conditions(row.get("conditions", ""))
        clean_conditions = []
        for c in conditions:
            if is_drug_name(c):
                qa_issues["drug_as_condition"].append((row.get("nct_id", ""), c))
            else:
                clean_conditions.append(c)

        if not conditions:
            qa_issues["empty_conditions"].append(row.get("nct_id", ""))

        if not row.get("intervention_names"):
            qa_issues["empty_interventions"].append(row.get("nct_id", ""))

        if not row.get("phase"):
            qa_issues["missing_phase"].append(row.get("nct_id", ""))

        if not row.get("status"):
            qa_issues["missing_status"].append(row.get("nct_id", ""))

        # Build cleaned row
        row["conditions_raw"] = row.get("conditions", "")
        row["conditions"] = "|".join(clean_conditions)
        row["conditions_flagged"] = "|".join(
            c for c in conditions if is_drug_name(c)
        )
        row["posted_year"] = extract_year(row.get("first_posted", ""))
        row["start_year"] = extract_year(row.get("start_date", ""))

        cleaned.append(row)

    # Save cleaned CSV
    out_path = os.path.join(DATA_DIR, "cleaned_trials.csv")
    write_csv(cleaned, out_path)
    print(f"Saved {len(cleaned)} cleaned rows to {out_path}")

    # QA report
    qa_path = os.path.join(DATA_DIR, "qa_report.txt")
    total_issues = sum(len(v) for v in qa_issues.values())
    with open(qa_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("DATA QUALITY REPORT\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Total rows: {len(cleaned)}\n")
        f.write(f"Total issues found: {total_issues}\n\n")

        f.write(f"Drug names listed as conditions: {len(qa_issues['drug_as_condition'])}\n")
        for nct, drug in qa_issues["drug_as_condition"]:
            f.write(f"  {nct}: '{drug}'\n")

        f.write(f"\nEncoding issues fixed: {len(qa_issues['encoding_fixed'])}\n")
        for nct, field in qa_issues["encoding_fixed"][:20]:
            f.write(f"  {nct}: field '{field}'\n")
        if len(qa_issues["encoding_fixed"]) > 20:
            f.write(f"  ... and {len(qa_issues['encoding_fixed']) - 20} more\n")

        f.write(f"\nEmpty conditions: {len(qa_issues['empty_conditions'])}\n")
        for nct in qa_issues["empty_conditions"][:10]:
            f.write(f"  {nct}\n")

        f.write(f"\nEmpty interventions: {len(qa_issues['empty_interventions'])}\n")
        f.write(f"Missing phase: {len(qa_issues['missing_phase'])}\n")
        f.write(f"Missing status: {len(qa_issues['missing_status'])}\n")

    print(f"QA report: {qa_path} ({total_issues} issues)")


if __name__ == "__main__":
    main()
