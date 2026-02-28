#!/usr/bin/env python3
"""
01_fetch_trials.py — Fetch all GLP-1 / GLP-1 RA clinical trials from ClinicalTrials.gov API v2.

Queries multiple search terms, deduplicates by NCT ID, flattens the nested JSON,
and saves both raw JSON and a flat CSV.
"""

import json
import os
import time
import urllib.parse
import urllib.request

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

FIELDS = [
    "NCTId", "BriefTitle", "OfficialTitle", "OverallStatus", "Phase",
    "StudyType", "Condition", "InterventionType", "InterventionName",
    "LeadSponsorName", "LeadSponsorClass", "EnrollmentCount", "StartDate",
    "StudyFirstPostDate", "CompletionDate", "PrimaryOutcomeMeasure",
    "Keyword", "DesignAllocation", "DesignPrimaryPurpose",
]

SEARCH_TERMS = [
    "GLP-1 receptor agonist",
    "semaglutide",
    "liraglutide",
    "tirzepatide",
    "exenatide",
    "dulaglutide",
    "lixisenatide",
    "albiglutide",
    "GLP-1",
    "incretin mimetic",
    "GIP/GLP-1",
]

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def fetch_studies(term, page_size=1000):
    """Fetch all studies matching a search term, handling pagination."""
    studies = []
    params = {
        "query.term": term,
        "fields": ",".join(FIELDS),
        "pageSize": str(page_size),
        "countTotal": "true",
        "format": "json",
    }
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    page = 1

    while url:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                break
            except Exception as e:
                if attempt < 2:
                    print(f"    Retry {attempt + 1} for '{term}' page {page}: {e}")
                    time.sleep(2 ** attempt)
                else:
                    print(f"    FAILED '{term}' page {page}: {e}")
                    return studies

        batch = data.get("studies", [])
        studies.extend(batch)
        total = data.get("totalCount", "?")
        print(f"    Page {page}: got {len(batch)} studies (total so far: {len(studies)}/{total})")

        token = data.get("nextPageToken")
        if token:
            next_params = dict(params)
            next_params["pageToken"] = token
            url = f"{BASE_URL}?{urllib.parse.urlencode(next_params)}"
            page += 1
            time.sleep(0.3)  # be polite
        else:
            url = None

    return studies


def safe_get(d, *keys, default=""):
    """Navigate nested dicts safely."""
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, {})
        else:
            return default
    return d if d and d != {} else default


def flatten_study(study):
    """Flatten a nested study JSON into a flat dict."""
    ps = study.get("protocolSection", {})
    ident = ps.get("identificationModule", {})
    status = ps.get("statusModule", {})
    sponsor = ps.get("sponsorCollaboratorsModule", {})
    cond = ps.get("conditionsModule", {})
    design = ps.get("designModule", {})
    arms = ps.get("armsInterventionsModule", {})
    outcomes = ps.get("outcomesModule", {})

    # Interventions
    interventions = arms.get("interventions", [])
    int_names = [i.get("name", "") for i in interventions]
    int_types = [i.get("type", "") for i in interventions]

    # Primary outcomes
    prim_outcomes = outcomes.get("primaryOutcomes", [])
    prim_measures = [o.get("measure", "") for o in prim_outcomes]

    # Phases
    phases = design.get("phases", [])

    # Conditions
    conditions = cond.get("conditions", [])

    # Keywords
    keywords = cond.get("keywords", [])

    return {
        "nct_id": ident.get("nctId", ""),
        "brief_title": ident.get("briefTitle", ""),
        "official_title": ident.get("officialTitle", ""),
        "status": status.get("overallStatus", ""),
        "phase": "|".join(phases) if phases else "",
        "study_type": design.get("studyType", ""),
        "conditions": "|".join(conditions),
        "intervention_names": "|".join(int_names),
        "intervention_types": "|".join(int_types),
        "sponsor_name": safe_get(sponsor, "leadSponsor", "name"),
        "sponsor_class": safe_get(sponsor, "leadSponsor", "class"),
        "enrollment": safe_get(design, "enrollmentInfo", "count", default=""),
        "start_date": safe_get(status, "startDateStruct", "date"),
        "first_posted": safe_get(status, "studyFirstPostDateStruct", "date"),
        "completion_date": safe_get(status, "completionDateStruct", "date"),
        "primary_outcomes": "|".join(prim_measures),
        "keywords": "|".join(keywords),
        "allocation": safe_get(design, "designInfo", "allocation"),
        "primary_purpose": safe_get(design, "designInfo", "primaryPurpose"),
    }


def write_csv(rows, path):
    """Write a list of dicts as CSV (no pandas dependency)."""
    if not rows:
        return
    headers = list(rows[0].keys())
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(headers) + "\n")
        for row in rows:
            vals = []
            for h in headers:
                v = str(row.get(h, ""))
                # Escape CSV
                if "," in v or '"' in v or "\n" in v:
                    v = '"' + v.replace('"', '""') + '"'
                vals.append(v)
            f.write(",".join(vals) + "\n")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    all_studies_raw = {}  # nct_id -> raw study JSON (dedup)
    for term in SEARCH_TERMS:
        print(f"\nSearching: '{term}'")
        studies = fetch_studies(term)
        new = 0
        for s in studies:
            nct = safe_get(s, "protocolSection", "identificationModule", "nctId")
            if nct and nct not in all_studies_raw:
                all_studies_raw[nct] = s
                new += 1
        print(f"  -> {len(studies)} results, {new} new (total unique: {len(all_studies_raw)})")

    print(f"\n{'='*60}")
    print(f"Total unique studies: {len(all_studies_raw)}")
    print(f"{'='*60}")

    # Save raw JSON
    raw_path = os.path.join(DATA_DIR, "raw_trials.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(list(all_studies_raw.values()), f, indent=2)
    print(f"Saved raw JSON: {raw_path}")

    # Flatten and save CSV
    flat = [flatten_study(s) for s in all_studies_raw.values()]
    csv_path = os.path.join(DATA_DIR, "raw_trials.csv")
    write_csv(flat, csv_path)
    print(f"Saved CSV ({len(flat)} rows): {csv_path}")


if __name__ == "__main__":
    main()
