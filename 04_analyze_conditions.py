#!/usr/bin/env python3
"""
04_analyze_conditions.py — Analyze conditions across classified trials.

- Explode conditions → one row per condition per trial
- Normalize condition variants (T2DM → "Type 2 Diabetes", etc.)
- Build frequency table
- Map to broad therapeutic categories
- Save conditions_expanded.csv and condition_summary.csv
"""

import csv
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

# ─── Condition normalization rules ───────────────────────────────────────────
# Maps (regex pattern) → canonical name.  Checked in order; first match wins.
CONDITION_ALIASES = [
    # Diabetes type 2
    (r"\btype\s*2\s*diabet|t2d|diabetes mellitus,?\s*type\s*2|niddm|dm2|"
     r"type\s*ii\s*diabet", "Type 2 Diabetes"),
    # Diabetes type 1
    (r"\btype\s*1\s*diabet|t1d|diabetes mellitus,?\s*type\s*1|iddm|dm1|"
     r"type\s*i\s*diabet", "Type 1 Diabetes"),
    # General diabetes (catch-all after specific types)
    (r"\bdiabetes mellitus\b(?!\s*,?\s*type)", "Diabetes Mellitus"),
    # Plain "Diabetes" catch-all
    (r"^diabetes$", "Diabetes Mellitus"),
    # Obesity / overweight
    (r"\bobes|overweight|body weight|weight loss|weight management|"
     r"weight reduction|adipos", "Obesity / Overweight"),
    # NASH / NAFLD / MASLD / liver
    (r"\bnash\b|non.?alcoholic steato|nafld|masld|mash\b|metabolic.?associated steatotic|"
     r"hepatic steatosis|fatty liver", "NASH / NAFLD"),
    # Cardiovascular
    (r"\bcardiovasc|heart failure|atherosclero|coronary|myocardial|"
     r"stroke|cerebrovascular|peripheral arter|heart disease|hfref|hfpef|"
     r"atrial fibr|major adverse cardiovascular", "Cardiovascular Disease"),
    # Chronic kidney / renal
    (r"\bchronic kidney|ckd\b|renal|diabetic kidney|kidney disease|"
     r"nephropathy|albuminuria", "Kidney / Renal Disease"),
    # Alzheimer / dementia / neuro
    (r"\balzheimer|dementia|cognitive|neurodegenerat|parkinson|"
     r"mild cognitive impairment", "Neurological / Cognitive"),
    # Metabolic syndrome
    (r"\bmetabolic syndrome|insulin resistance|prediabet|glucose intolerance|"
     r"hyperglycemia|dysglycemia|impaired glucose", "Metabolic Syndrome / Prediabetes"),
    # Sleep apnea
    (r"\bsleep apnea|obstructive sleep", "Sleep Apnea"),
    # Cancer / oncology
    (r"\bcancer|carcinoma|tumor|neoplasm|oncol|malignan", "Cancer"),
    # Polycystic ovary
    (r"\bpcos\b|polycystic ovar", "PCOS"),
    # Substance use / addiction
    (r"\balcohol|substance use|addiction|opioid|tobacco|smoking|"
     r"binge eating", "Substance Use / Addiction"),
    # Diabetic retinopathy / eye
    (r"\bretinopathy|macular|diabet.+eye", "Diabetic Retinopathy"),
    # Diabetic neuropathy
    (r"\bneuropathy|diabetic nerve", "Diabetic Neuropathy"),
    # Inflammation / immune
    (r"\binflammation|inflammatory|autoimmune|rheumatoid|psoriasis|"
     r"crohn|colitis|ibd\b", "Inflammation / Autoimmune"),
    # Hyperinsulinism
    (r"\bhyperinsulin", "Hyperinsulinism"),
    # Lipid / dyslipidemia
    (r"\bdyslipidemia|hyperlipidemia|cholesterol|lipid|triglycerid|"
     r"hypercholesterol", "Dyslipidemia"),
    # Hypertension
    (r"\bhypertension|high blood pressure", "Hypertension"),
    # Gastroparesis / GI
    (r"\bgastropares|gastroparesis|gastric empty|nausea|vomiting|"
     r"gastrointestinal", "GI / Gastroparesis"),
    # Healthy volunteers (merge variants)
    (r"^healthy\s*(volunteers?|subjects?|adults?|participants?|individuals?|controls?|people|persons?)?$",
     "Healthy Volunteers"),
    # Hypoglycemia
    (r"\bhypoglycemia|hypoglycaemia", "Hypoglycemia"),
]

# Broad therapeutic area mapping
BROAD_CATEGORIES = {
    "Type 2 Diabetes": "Metabolic / Diabetes",
    "Type 1 Diabetes": "Metabolic / Diabetes",
    "Diabetes Mellitus": "Metabolic / Diabetes",
    "Metabolic Syndrome / Prediabetes": "Metabolic / Diabetes",
    "Hyperinsulinism": "Metabolic / Diabetes",
    "Obesity / Overweight": "Obesity / Weight",
    "NASH / NAFLD": "NASH / Liver",
    "Cardiovascular Disease": "Cardiovascular",
    "Hypertension": "Cardiovascular",
    "Dyslipidemia": "Cardiovascular",
    "Kidney / Renal Disease": "Kidney / Renal",
    "Neurological / Cognitive": "Neurological",
    "Cancer": "Cancer",
    "Sleep Apnea": "Other",
    "PCOS": "Other",
    "Substance Use / Addiction": "Other",
    "Diabetic Retinopathy": "Metabolic / Diabetes",
    "Diabetic Neuropathy": "Metabolic / Diabetes",
    "Inflammation / Autoimmune": "Other",
    "GI / Gastroparesis": "Other",
    "Healthy Volunteers": "Other",
    "Hypoglycemia": "Metabolic / Diabetes",
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


def normalize_condition(cond):
    """Normalize a single condition string to a canonical name."""
    cond_lower = cond.strip().lower()
    if not cond_lower:
        return None
    for pattern, canonical in CONDITION_ALIASES:
        if re.search(pattern, cond_lower, re.IGNORECASE):
            return canonical
    return cond.strip()  # Keep original if no match


def get_broad_category(normalized_condition):
    """Map a normalized condition to a broad category."""
    return BROAD_CATEGORIES.get(normalized_condition, "Other")


def main():
    input_path = os.path.join(DATA_DIR, "classified_trials.csv")
    if not os.path.exists(input_path):
        print(f"ERROR: {input_path} not found. Run 03_classify_mechanisms.py first.")
        return

    rows = read_csv(input_path)
    print(f"Loaded {len(rows)} classified trials")

    # ── Explode conditions ───────────────────────────────────────────────────
    expanded = []
    for row in rows:
        conditions = row.get("conditions", "")
        if not conditions:
            # Keep the trial even if no conditions
            new_row = dict(row)
            new_row["condition_individual"] = ""
            new_row["condition_normalized"] = "Unknown"
            new_row["condition_broad_category"] = "Other"
            expanded.append(new_row)
            continue

        parts = [c.strip() for c in conditions.split("|") if c.strip()]
        for cond in parts:
            new_row = dict(row)
            new_row["condition_individual"] = cond
            normalized = normalize_condition(cond)
            new_row["condition_normalized"] = normalized if normalized else "Unknown"
            new_row["condition_broad_category"] = get_broad_category(
                new_row["condition_normalized"]
            )
            expanded.append(new_row)

    print(f"Expanded to {len(expanded)} condition-trial rows")

    # ── Save expanded ────────────────────────────────────────────────────────
    exp_path = os.path.join(DATA_DIR, "conditions_expanded.csv")
    write_csv(expanded, exp_path)
    print(f"Saved {exp_path}")

    # ── Build condition frequency table ──────────────────────────────────────
    condition_counts = {}
    broad_counts = {}
    for row in expanded:
        cn = row["condition_normalized"]
        bc = row["condition_broad_category"]
        condition_counts[cn] = condition_counts.get(cn, 0) + 1
        broad_counts[bc] = broad_counts.get(bc, 0) + 1

    # Sort by count descending
    summary = []
    for cond, count in sorted(condition_counts.items(), key=lambda x: -x[1]):
        summary.append({
            "condition_normalized": cond,
            "broad_category": get_broad_category(cond),
            "trial_count": count,
        })

    sum_path = os.path.join(DATA_DIR, "condition_summary.csv")
    write_csv(summary, sum_path)
    print(f"Saved {sum_path}")

    # ── Print summaries ──────────────────────────────────────────────────────
    print(f"\nTop 20 Normalized Conditions:")
    for s in summary[:20]:
        print(f"  {s['trial_count']:>5}  {s['condition_normalized']}")

    print(f"\nBroad Categories:")
    for bc, count in sorted(broad_counts.items(), key=lambda x: -x[1]):
        print(f"  {count:>5}  {bc}")


if __name__ == "__main__":
    main()
