#!/usr/bin/env python3
"""
03_classify_mechanisms.py — Classify each trial by drug mechanism and therapy type.

Reads cleaned_trials.csv and adds:
  - mechanism_class: GLP-1 RA, GIP/GLP-1 Dual, Triple Agonist, etc.
  - therapy_type: monotherapy, combination, non-drug
  - specific_drugs: list of matched drug names
"""

import csv
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

# Drug → mechanism class mapping
DRUG_MECHANISMS = {
    # GLP-1 RA (injectable)
    "semaglutide": "GLP-1 RA",
    "liraglutide": "GLP-1 RA",
    "exenatide": "GLP-1 RA",
    "dulaglutide": "GLP-1 RA",
    "lixisenatide": "GLP-1 RA",
    "albiglutide": "GLP-1 RA",
    # Brand names
    "ozempic": "GLP-1 RA",
    "wegovy": "GLP-1 RA",
    "victoza": "GLP-1 RA",
    "saxenda": "GLP-1 RA",
    "trulicity": "GLP-1 RA",
    "byetta": "GLP-1 RA",
    "bydureon": "GLP-1 RA",
    "rybelsus": "GLP-1 RA",
    "adlyxin": "GLP-1 RA",
    "tanzeum": "GLP-1 RA",
    "soliqua": "GLP-1 RA",
    "xultophy": "GLP-1 RA",
    # Oral GLP-1 RA (novel)
    "orforglipron": "Oral GLP-1 RA",
    "danuglipron": "Oral GLP-1 RA",
    # GIP/GLP-1 dual agonist
    "tirzepatide": "GIP/GLP-1 Dual Agonist",
    "mounjaro": "GIP/GLP-1 Dual Agonist",
    "zepbound": "GIP/GLP-1 Dual Agonist",
    # GLP-1/Glucagon dual
    "survodutide": "GLP-1/Glucagon Dual Agonist",
    "cotadutide": "GLP-1/Glucagon Dual Agonist",
    "efinopegdutide": "GLP-1/Glucagon Dual Agonist",
    "pemvidutide": "GLP-1/Glucagon Dual Agonist",
    "mazdutide": "GLP-1/Glucagon Dual Agonist",
    "BI 456906": "GLP-1/Glucagon Dual Agonist",
    # Triple agonist (GIP/GLP-1/Glucagon)
    "retatrutide": "Triple Agonist (GIP/GLP-1/Glucagon)",
    # Amylin analogs (often combined with GLP-1)
    "cagrilintide": "Amylin Analog",
}

# Other drugs that might appear alongside GLP-1 RAs
COMBO_DRUGS = {
    "insulin", "metformin", "empagliflozin", "dapagliflozin", "canagliflozin",
    "sitagliptin", "linagliptin", "saxagliptin", "alogliptin", "glimepiride",
    "pioglitazone", "ertugliflozin", "sotagliflozin",
}


def read_csv(path):
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(rows, path):
    if not rows:
        return
    headers = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def classify_study(row):
    """Classify a study's mechanism based on intervention names, title, keywords."""
    # Combine all text sources for matching
    text_sources = " | ".join([
        row.get("intervention_names", ""),
        row.get("brief_title", ""),
        row.get("official_title", ""),
        row.get("keywords", ""),
    ]).lower()

    matched_drugs = []
    matched_classes = set()
    has_combo_drug = False

    # Check for known GLP-1 class drugs
    for drug, mech_class in DRUG_MECHANISMS.items():
        if drug.lower() in text_sources:
            matched_drugs.append(drug)
            matched_classes.add(mech_class)

    # Check for combination drugs
    for drug in COMBO_DRUGS:
        if drug.lower() in text_sources:
            has_combo_drug = True

    # Determine mechanism class (prioritize most specific)
    if "Triple Agonist (GIP/GLP-1/Glucagon)" in matched_classes:
        mechanism = "Triple Agonist"
    elif "GLP-1/Glucagon Dual Agonist" in matched_classes:
        mechanism = "GLP-1/Glucagon Dual"
    elif "GIP/GLP-1 Dual Agonist" in matched_classes:
        mechanism = "GIP/GLP-1 Dual"
    elif "Oral GLP-1 RA" in matched_classes:
        mechanism = "Oral GLP-1 RA"
    elif "GLP-1 RA" in matched_classes:
        mechanism = "GLP-1 RA"
    elif "Amylin Analog" in matched_classes:
        mechanism = "Amylin/GLP-1"
    elif re.search(r"glp.?1", text_sources):
        mechanism = "GLP-1 Related (unspecified)"
    else:
        mechanism = "Other/Unknown"

    # Determine therapy type
    int_types = row.get("intervention_types", "").lower()
    int_names = row.get("intervention_names", "").lower()

    if "drug" not in int_types and "biological" not in int_types:
        therapy_type = "Non-drug"
    elif len(matched_classes) > 1 or has_combo_drug:
        therapy_type = "Combination"
    elif len(matched_drugs) == 1:
        therapy_type = "Monotherapy"
    elif len(matched_drugs) > 1:
        # Multiple drugs from same class still = combination
        unique_drugs = set(d.lower() for d in matched_drugs)
        # Remove brand/generic duplicates
        if len(unique_drugs) > 1:
            therapy_type = "Combination"
        else:
            therapy_type = "Monotherapy"
    else:
        therapy_type = "Unknown"

    return mechanism, therapy_type, "|".join(sorted(set(matched_drugs)))


def main():
    input_path = os.path.join(DATA_DIR, "cleaned_trials.csv")
    if not os.path.exists(input_path):
        print(f"ERROR: {input_path} not found. Run 02_clean_data.py first.")
        return

    rows = read_csv(input_path)
    print(f"Loaded {len(rows)} rows from cleaned_trials.csv")

    # Classify each study
    for row in rows:
        mech, therapy, drugs = classify_study(row)
        row["mechanism_class"] = mech
        row["therapy_type"] = therapy
        row["specific_drugs"] = drugs

    # Print summary
    mech_counts = {}
    therapy_counts = {}
    for row in rows:
        m = row["mechanism_class"]
        t = row["therapy_type"]
        mech_counts[m] = mech_counts.get(m, 0) + 1
        therapy_counts[t] = therapy_counts.get(t, 0) + 1

    print("\nMechanism Classification:")
    for mech, count in sorted(mech_counts.items(), key=lambda x: -x[1]):
        print(f"  {mech}: {count}")

    print("\nTherapy Type:")
    for t, count in sorted(therapy_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {count}")

    # Save
    out_path = os.path.join(DATA_DIR, "classified_trials.csv")
    write_csv(rows, out_path)
    print(f"\nSaved {len(rows)} classified rows to {out_path}")


if __name__ == "__main__":
    main()
