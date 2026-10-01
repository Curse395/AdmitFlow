# AdmitFlow — Synthetic Admission-Funnel Dataset

> The primary project dataset is synthetic and was generated according to the documented
> AdmitFlow admission-funnel specification for development, experimentation, evaluation, and
> demonstration. It does not represent any real institution, applicant, or admission outcome.

> Any metric computed on this dataset is a property of the documented generator assumptions.
> It must never be reported as real-world institutional performance.

A deterministic, fully documented, reproducible synthetic dataset for the T.Y. B.Sc. Data
Science capstone **ADMITFLOW** — *Admission Conversion Forecasting with Funnel Attribution and
Scenario Simulation*.

This repository contains **only the data foundation**: a written data contract, a generator, a
validator, a profiler, the generated data, and reports. It contains **no trained model and no
model-performance numbers**. Producing those is the next agent's job.

---

## Quick start

```powershell
python -m pip install -r requirements.txt

# 1. generate (deterministic; same seed -> byte-identical output)
python scripts/generate_dataset.py --n-applications 28000 --emit-data-dictionary

# 2. validate (exits non-zero on any FAIL)
python scripts/validate_dataset.py

# 3. profile (read-only; writes no model figures)
python scripts/profile_dataset.py
```

Current state: **436 validation checks, 0 fail, 0 warn.**

---

## What the dataset answers

| Question | Answer |
|---|---|
| Prediction unit | one **application** (one applicant's journey to one programme in one cycle) |
| Primary target | `enrolled_flag` — registration completed |
| Prediction point | `application_submitted_ts` |
| Secondary target | `enrolled_given_admitted_flag`, predicted at `admission_decision_ts` |
| Forecast grain | programme × admission cycle × ISO week (`fact_forecast_panel`) |
| Forecast target | `cum_enrolled` at origin + H, H ∈ {1, 2, 4, 6} weeks |
| Safe features | an explicit **allow-list** of 45 columns per feature set |

The funnel is a 7-stage ladder, prefix-closed and non-re-entrant:

| # | Stage | Step conversion | Top-of-funnel |
|---|---|---|---|
| 1 | `prospect` | — | 1.000 |
| 2 | `application_started` | 0.580 | 0.580 |
| 3 | `application_submitted` | 0.749 | 0.434 |
| 4 | `application_verified` | 0.824 | 0.358 |
| 5 | `admission_decision` | 0.983 | 0.352 |
| 6 | `admitted` | 0.480 | 0.169 |
| 7 | `enrolled` | 0.717 | 0.121 |

---

## Layout

```
admitflow-data/
├── README.md                     <- you are here
├── requirements.txt
├── data/
│   ├── raw/                      <- generated, never hand-edited
│   │   ├── dim_funnel_stage.csv        7 rows
│   │   ├── dim_region.csv              8 rows
│   │   ├── dim_programme.csv          12 rows
│   │   ├── dim_admission_cycle.csv     4 rows
│   │   ├── dim_campaign.csv           32 rows
│   │   ├── fact_applicant.csv     25,279 rows
│   │   ├── fact_application.csv   28,000 rows   <- central fact, 61 columns
│   │   ├── fact_funnel_event.csv  84,383 rows
│   │   ├── fact_engagement.csv    38,369 rows
│   │   ├── fact_forecast_panel.csv 2,064 rows
│   │   └── _manifest.json             config + row counts + SHA-256 per file
│   └── processed/
│       └── applications_modelling_view.csv   12,161 rows, 58 columns
├── docs/
│   ├── admitflow_data_contract.md   <- the binding analytical contract (read this first)
│   ├── data_dictionary.md           <- every field: role, availability, leakage, logic
│   └── dataset_handoff_report.md    <- what to read, in what order, and what is not here
├── scripts/
│   ├── admitflow_schema.py          <- single source of truth for the column registry
│   ├── generate_dataset.py          <- the generator (deterministic)
│   ├── validate_dataset.py          <- 6 check families, 436 checks
│   └── profile_dataset.py           <- descriptive profile (no model figures)
└── reports/
    ├── validation_report.md
    └── profiling_report.md
```

---

## The three rules that matter

**1. `scripts/admitflow_schema.py` is the single source of truth.**
Entities, columns, roles, availability, leakage risk and feature-set membership are declared
once. `docs/data_dictionary.md` is *rendered* from it (`--emit-data-dictionary`), and the
validator reads the same registry. The contract, the data and the documentation therefore
cannot drift apart.

**2. The data is generated, never edited.**
No CSV row is ever hand-written or patched. Every defect found by the validator is fixed in
the generator or the schema and the dataset is regenerated from scratch. This is what makes the
dataset reproducible.

**3. The leakage boundary is machine-verified, not merely documented.**
Columns are classified `GENERATED` / `DERIVED` / `TARGET` / `POST_OUTCOME`. Safe features are
an allow-list, not a blocklist. The validator checks against the *data* that every feature's
source timestamp is at or before the prediction point, and **fails** if any post-outcome column
reaches a feature set. `selection_score` is retained in the raw data on purpose as a trap.

---

## Attribution is not causation

`acquisition_channel`, `acquisition_source`, `campaign_id`, `touchpoints_count` and
`is_multi_touch` record which marketing touch an application is **associated** with. They
support cross-source comparison of volume and conversion. Programme mix, cycle mix and
applicant composition differ across channels, so a channel-level yield gap is **confounded**.
This dataset does not support, and must not be used to make, a causal claim about marketing
spend.

---

## Reproducibility

```powershell
# same seed, byte-identical output - verified by comparing the manifest
python scripts/generate_dataset.py --n-applications 28000
(Get-Content data/raw/_manifest.json -Raw)
python scripts/generate_dataset.py --n-applications 28000
(Get-Content data/raw/_manifest.json -Raw)
```

`data/raw/_manifest.json` records the seed, the full generator config, row counts and a SHA-256
for every file. It is the artefact to quote when claiming the dataset is unchanged.

### Useful flags

```
--n-applications N      target application count (default 28000; 10k-30k is the designed range)
--n-cycles N            number of admission cycles (default 4)
--start-cycle-year Y    first cycle year (default 2022)
--seed S                random seed (default 20240817)
--min-history-weeks W   panel history required before a week is a forecast origin (default 4)
--root PATH             output root (default: parent of scripts/; no machine-specific paths)
--emit-data-dictionary  also write docs/data_dictionary.md from the schema registry
```

```powershell
# a smaller dataset for quick iteration
python scripts/generate_dataset.py --n-applications 12000 --n-cycles 3
```

---

## Known limitations

See `docs/dataset_handoff_report.md` for the full list. The most important ones:

- **Synthetic.** Every number is a property of the generator, not of any real institution.
- **Non-causal attribution.** Channel fields are associational only.
- **Waits are out of scope.** There is no waitlist sub-process; admission is a single
  milestone.
- **Enrolment is one milestone.** Registration and the first fee instalment are a single
  event, not a separate deposit step.
- **Two cycles in train.** With `--n-cycles 4` the chronological split is 2 train / 1
  validation / 1 test, which is thin for a rolling-origin backtest.
- **Open questions** (T-01..T-05) remain on region granularity, the scholarship sub-process,
  a deposit/fee split, cross-cycle re-engagement features, and target-cycle holdout vs
  rolling-origin backtest.

---

## Where to start reading

1. `docs/dataset_handoff_report.md` — orientation and the exact file list
2. `docs/admitflow_data_contract.md` — funnel, prediction unit, target, horizon, entities
3. `docs/data_dictionary.md` — every field, its availability and its leakage risk
4. `reports/validation_report.md` — what has been machine-checked
5. `reports/profiling_report.md` — what the data actually looks like
