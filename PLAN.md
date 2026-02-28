# GLP-1 Clinical Trial Analysis — Replication Plan

## Objective

Replicate a clinical trials analysis of GLP-1 receptor agonists by pulling data from ClinicalTrials.gov, cleaning it, classifying drug mechanisms, analyzing conditions, and generating publication-quality charts and a summary report.

## Data Source

**ClinicalTrials.gov API v2** — no authentication required.

| Parameter | Value |
|-----------|-------|
| Base URL | `https://clinicaltrials.gov/api/v2/studies` |
| Pagination | `pageSize=1000`, `nextPageToken` for subsequent pages |
| Format | `format=json` |
| Count | `countTotal=true` |
| Query | `query.term=<URL-encoded search term>` |
| Fields | `fields=NCTId,BriefTitle,OfficialTitle,OverallStatus,Phase,StudyType,Condition,InterventionType,InterventionName,LeadSponsorName,LeadSponsorClass,EnrollmentCount,StartDate,StudyFirstPostDate,CompletionDate,PrimaryOutcomeMeasure,Keyword,DesignAllocation,DesignPrimaryPurpose` |

**Response structure:** deeply nested JSON under `protocolSection` → module-specific keys. Studies are in `studies[]`, pagination via `nextPageToken`, total via `totalCount`.

## Search Terms

```
GLP-1 receptor agonist, semaglutide, liraglutide, tirzepatide,
exenatide, dulaglutide, lixisenatide, albiglutide,
GLP-1, incretin mimetic, GIP/GLP-1
```

## Pipeline

### Step 1 — Fetch (`01_fetch_trials.py`)

- Query each search term, paginate through all results
- Deduplicate by NCT ID across all queries
- Flatten nested JSON into a flat dict per study
- Save `data/raw_trials.json` (full responses) and `data/raw_trials.csv` (flattened)
- Retry on transient errors; print progress

### Step 2 — Clean (`02_clean_data.py`)

- Normalize conditions: split on `,` `;` `|`, strip whitespace
- Flag drug-as-condition entries (semaglutide, tirzepatide, liraglutide, etc.)
- Unicode normalization (NFKD), fix encoding artifacts
- Extract `posted_year` from `StudyFirstPostDate`
- Generate `data/qa_report.txt` with issue counts
- Save `data/cleaned_trials.csv`

### Step 3 — Classify Mechanisms (`03_classify_mechanisms.py`)

| Classification | Drugs |
|----------------|-------|
| GLP-1 RA | semaglutide, liraglutide, exenatide, dulaglutide, lixisenatide, albiglutide |
| GIP/GLP-1 Dual Agonist | tirzepatide |
| GLP-1/Glucagon Dual | survodutide, cotadutide, efinopegdutide, pemvidutide, mazdutide |
| Triple Agonist | retatrutide |
| Oral GLP-1 RA | oral semaglutide, orforglipron, danuglipron |
| Other/Unknown | everything else |

Also tags: monotherapy vs. combination, intervention type (drug/behavioral/device).

Save `data/classified_trials.csv`.

### Step 4 — Analyze Conditions (`04_analyze_conditions.py`)

- Explode conditions → one row per condition per trial
- Normalize variants (T2DM / Type 2 Diabetes Mellitus → "Type 2 Diabetes")
- Build frequency table
- Map to broad categories: Metabolic/Diabetes, Obesity/Weight, NASH/Liver, Cardiovascular, Kidney/Renal, Neurological, Cancer, Other
- Save `data/conditions_expanded.csv`, `data/condition_summary.csv`

### Step 5 — Visualize (`05_visualize.py`)

Seven charts saved to `output/charts/`:

1. `trials_per_year.png` — bar chart with most recent year highlighted
2. `phase_distribution.png` — horizontal bar chart
3. `phase_by_year.png` — stacked bar chart
4. `drug_class_distribution.png` — horizontal bar chart
5. `condition_wheel.png` — donut chart of top 15 conditions
6. `status_distribution.png` — pie chart
7. `sponsor_types.png` — bar chart

### Step 6 — Report (`06_report.py`)

Generates `output/report.md` with executive summary, data quality section, tables for key breakdowns, chart image references, and a note about the pistachio study.

## Directory Structure

```
iu-talk/
├── 01_fetch_trials.py
├── 02_clean_data.py
├── 03_classify_mechanisms.py
├── 04_analyze_conditions.py
├── 05_visualize.py
├── 06_report.py
├── PLAN.md
├── data/
│   ├── raw_trials.json
│   ├── raw_trials.csv
│   ├── cleaned_trials.csv
│   ├── classified_trials.csv
│   ├── conditions_expanded.csv
│   ├── condition_summary.csv
│   └── qa_report.txt
├── output/
│   ├── report.md
│   └── charts/
│       ├── trials_per_year.png
│       ├── phase_distribution.png
│       ├── phase_by_year.png
│       ├── drug_class_distribution.png
│       ├── condition_wheel.png
│       ├── status_distribution.png
│       └── sponsor_types.png
├── transcript.md
├── screenshots/
└── frames/
```

## Dependencies

```bash
pip install requests pandas matplotlib seaborn
```

## Execution

```bash
python 01_fetch_trials.py          # ~2 min (API calls + pagination)
python 02_clean_data.py            # seconds
python 03_classify_mechanisms.py   # seconds
python 04_analyze_conditions.py    # seconds
python 05_visualize.py             # seconds
python 06_report.py                # seconds
```

Each script is self-contained and runnable independently.
