# AdmitFlow — Dataset Handoff Report

**From:** Dataset Engineering Agent
**To:** AdmitFlow orchestration / modelling agents
**Scope:** synthetic data foundation only. No model was trained and no model-performance number
is reported anywhere in this deliverable.

> The primary project dataset is synthetic and was generated according to the documented
> AdmitFlow admission-funnel specification for development, experimentation, evaluation, and
> demonstration. It does not represent any real institution, applicant, or admission outcome.

> Any metric computed on this dataset is a property of the documented generator assumptions.
> It must never be reported as real-world institutional performance.

---

## 1. What was produced

| Item | Value |
|---|---|
| Application-level records | **28,000** (inside the 10,000–30,000 brief) |
| Total rows across 10 tables | **178,095** |
| Admission cycles | 4, AY2022–AY2025, **all fully closed** |
| Programmes | 12 |
| Regions | 8 |
| Campaigns | 32 (2 intake rounds × 4 cycles × campaign channels) |
| Temporal coverage | 2022-06-10 → 2026-02-26 (**44 months**) |
| Primary modelling view | 12,161 submitted applications × 58 columns |
| Forecast panel | 2,064 cells (12 × 4 × 43 weeks), **552 eligible forecast origins** |
| Safe features | 45 per feature set, 2 feature sets |
| Validation | **436 checks — 0 fail, 0 warn** |
| Reproducibility | same seed → byte-identical `_manifest.json` (verified) |

The dataset is **fictional throughout**. No real applicant, institution, campaign or admission
outcome is represented, and no external dataset was copied.

---

## 2. Files — bring these back to the orchestration chat

| # | File | What it is for |
|---|---|---|
| 1 | `docs/admitflow_data_contract.md` | **The binding contract.** Funnel definition, prediction unit, target, forecast design, entity model, decision log D-01..D-15, open questions T-01..T-05, invariants F1–F5, rules R1–R6, limitations L-01..L-12. |
| 2 | `docs/data_dictionary.md` | **Every field of every table**, classified `GENERATED`/`DERIVED`/`TARGET`/`POST_OUTCOME`, with availability at prediction time, leakage risk, feature-set membership, generation logic and a real example value pulled from the generated data. |
| 3 | `docs/dataset_handoff_report.md` | This file. |
| 4 | `scripts/admitflow_schema.py` | **Single source of truth.** The column registry. Edit here, never in the CSV. |
| 5 | `scripts/generate_dataset.py` | Deterministic generator. |
| 6 | `scripts/validate_dataset.py` | 6 check families, 436 checks. |
| 7 | `scripts/profile_dataset.py` | Descriptive profile. Contains no model figures. |
| 8 | `data/raw/` (10 CSVs + `_manifest.json`) | The generated data. |
| 9 | `data/processed/applications_modelling_view.csv` | Ready-to-model denormalised extract. |
| 10 | `reports/validation_report.md` | Machine-checked evidence. |
| 11 | `reports/profiling_report.md` | Descriptive evidence. |
| 12 | `README.md`, `requirements.txt` | Orientation and dependencies (numpy, pandas only). |

The data itself (~28 MB of CSV) is reproducible from item 4 + item 5 alone. If the chat cannot
carry the CSVs, carry items 1–4 and regenerate.

---

## 3. Read in this order

1. `admitflow_data_contract.md` §B (funnel) and §C–D (unit and target) — 10 minutes.
2. `data_dictionary.md` — look up any column you intend to use; check its **Availability** and
   **Leakage risk** before you use it.
3. `reports/validation_report.md` — the ML family, especially the `leakage.*` checks.
4. `reports/profiling_report.md` — the funnel and segment tables, so you know what variation
   exists to model.

---

## 4. The analytical contract, in brief

### 4.1 Funnel (7 stages, prefix-closed, non-re-entrant)

An application enters at `prospect` and either advances one stage or terminates with a
`dropoff_stage` + `dropoff_reason`. Stages are never skipped and never revisited (invariant F1).

| # | Stage | Reached (cum.) | Step conv. | Top-of-funnel |
|---|---|---|---|---|
| 1 | `prospect` | 28,000 | — | 1.000 |
| 2 | `application_started` | 16,230 | 0.580 | 0.580 |
| 3 | `application_submitted` | 12,161 | 0.749 | 0.434 |
| 4 | `application_verified` | 10,023 | 0.824 | 0.358 |
| 5 | `admission_decision` | 9,854 | 0.983 | 0.352 |
| 6 | `admitted` | 4,727 | 0.480 | 0.169 |
| 7 | `enrolled` | 3,388 | 0.717 | **0.121** |

Drop-off reasons are stage-specific and **weighted** — not uniform. The largest single exit is
`no_response` at the prospect stage (5,863), then `below_merit_cutoff` at decision (3,621), then
`form_abandoned` after starting (1,841), then `incomplete_documents` after submitting (1,579).

### 4.2 Prediction unit

**One application** = one applicant's journey to one programme in one admission cycle.

Rejected alternatives, and why:

- *applicant* — "conversion" is ambiguous at applicant level, and applications are not
  independent rows, so a naive model would double-count. Applicants **do** appear 1..N times
  (25,279 applicants for 28,000 applications), so this was tested, not assumed.
- *cohort (programme × cycle)* — reserved for forecasting, where it is the right grain.

If you fit at applicant level, **group your folds by `applicant_id`**, or the same applicant
will appear in both train and test.

### 4.3 Targets

| Target | Meaning | Predicted at | Positive rate |
|---|---|---|---|
| `enrolled_flag` **(primary)** | registration completed | `application_submitted_ts` | 0.279 (12,161 rows) |
| `enrolled_given_admitted_flag` **(secondary)** | registered, among those admitted | `admission_decision_ts` | 0.717 (4,727 rows) |
| `admitted_flag` **(tertiary)** | offer released | — (POST_OUTCOME) | 0.389 (12,161 rows) |

- **Prediction point:** `application_submitted_ts`. At that instant the primary feature set
  (45 columns) is fully available and nothing later has happened.
- **Outcome window:** from `application_submitted_ts` to the end of the cycle's registration
  window. The whole cycle is closed, so there is no right-censoring.
- **Modelling view population:** applications that reached `application_submitted`
  (12,161 of 28,000). Applications that dropped earlier are excluded from the *supervised*
  view but remain in `fact_application` and `fact_funnel_event` for funnel analytics.

### 4.4 Forecast design

- **Grain:** programme × admission cycle × ISO week (Monday start).
- **Origin `T`:** a week with `is_forecast_eligible = 1` — at least 4 weeks of history, on/after
  the intake-1 decision window opens, on/before cycle end, **and** with enough remaining weeks
  that `origin + H` is a real observed panel cell for every declared `H`.
- **Horizon `H`:** 1, 2, 4 or 6 weeks.
- **Frequency:** weekly, rolling origin.
- **Target:** `cum_enrolled` at `T + H` (cumulative), with `wk_*` increments available.
- **Panel:** 2,064 cells, 552 eligible origins, cumulative ladder non-increasing at every cell
  and reconciling **exactly** with `fact_application`.
- **Actual vs predicted:** the actual is the observed `cum_enrolled` at `T + H`, taken from the
  panel itself — never back-filled or interpolated. There is no leakage of future weeks into
  the feature set: use only panel columns with `week_index_in_cycle <= week_index_of(T)`.

### 4.5 Key features

Declared in `admitflow_schema.py` as allow-lists, 45 columns each:

- **Applicant context** — `region_id`, `gender_band`, `education_level`, `application_count`,
  `mean_distance_km_to_campus`, `is_repeat_applicant_at_prediction`
- **Programme / capacity** — `annual_fee_inr`, `base_seat_capacity`, `selectivity_tier`,
  `duration_years`, `review_duration_days`, `demand_weight`
- **Attribution (non-causal)** — `acquisition_channel`, `acquisition_source`, `campaign_id`,
  `touchpoints_count`, `is_multi_touch`, `is_referral_alumni`
- **Timing / intent** — `intake_round`, `days_inquiry_to_submit`, `days_start_to_submit`,
  `days_to_round_close_at_start`, `week_of_cycle_at_submission`, `month_of_submission`
- **Academic / documentation** — `academic_score_pct`, `academic_score_band`,
  `doc_completeness_score`, `fee_scholarship_applied`
- **Engagement (pre-submission)** — `pre_sub_session_count`, `pre_sub_active_days`,
  `pre_sub_total_minutes`, `pre_sub_doc_uploads`, `pre_sub_form_fields_completed`,
  `pre_sub_return_visits`

### 4.6 Safe features vs post-outcome

The two lists are disjoint by construction, and the validator fails the build if they ever
overlap.

| | Safe prediction features | Post-outcome fields (never features of the primary target) |
|---|---|---|
| Count | 45 | 20 in `fact_application` |
| Timing | dated ≤ `application_submitted_ts` | dated after it |
| Examples | `academic_score_pct`, `days_inquiry_to_submit`, `annual_fee_inr` | `selection_score`, `stage_reached`, `admitted_flag`, `enrolled_ts`, `application_verified_ts`, `doc_query_count` |
| Role | `GENERATED` / `DERIVED` | `POST_OUTCOME` / `TARGET` |

`selection_score` (the institution's internal merit score) is **deliberately retained** in the
raw data as a leakage trap, so that a leakage mistake is possible and therefore detectable. It
is absent from the modelling view, and the validator checks both.

---

## 5. Validation status and key statistics

**436 checks across 6 families: 0 FAIL, 0 WARN.**

| Family | Checks | Covers |
|---|---|---|
| `STRUCTURAL` | 153 | file presence, row counts, column sets, dtypes, PK uniqueness, FK integrity |
| `DATA` | 92 | nullability, duplicates, category domains, numeric ranges, campaign integrity |
| `FUNNEL` | 33 | invariants F1–F5, impossible transitions, panel ladder, reconciliation |
| `TEMPORAL` | 38 | cycle windows, intake-round deadlines, chronology, week grid, split, horizons |
| `ML` | 104 | target balance, role-based leakage, prediction-time boundary, perfect predictors |
| `REALISM` | 16 | distribution spread, funnel rates, segment variation, demand crowding |

Highlighted results:

| Check | Result |
|---|---|
| Reproducibility | two consecutive runs → byte-identical `_manifest.json` (SHA-256 per file) |
| Funnel F1 (prefix-closed staircase) | 28,000 applications, 0 skipped stages |
| Funnel F2 (strictly increasing events) | 0 violations after fixing the admit/decision tie |
| Panel ladder non-increasing | 0 violations across all 2,064 cells |
| Panel ↔ fact reconciliation | 0 mismatches (enrolled and submitted) |
| Null pattern vs funnel | exact match for all 6 stage-conditional columns |
| Leakage: post-outcome in feature set | none, in either feature set |
| Leakage: prediction-time boundary | every feature's source timestamp ≤ prediction point, on every row |
| Target not trivially predictable | strongest single safe feature rank AUC **0.713** (`doc_completeness_score`); threshold 0.93 |
| Chronological split | 2 train / 1 validation / 1 test, a pure function of `cycle_id` |
| Forecast horizons | 1w, 2w, 4w, 6w all fully observable at every eligible origin |

### Defects found by validation and fixed in the generator

The validator earned its keep. Each of these was a **generator or schema** fix, never a CSV
edit, followed by full regeneration:

1. `application_started_ts` was never written (100% null) while the funnel event existed —
   the column and the event had drifted apart.
2. 80 applications had `admission_decision_ts == admitted_ts`, breaking invariant F2. The offer
   is now dispatched 3–60 hours after the decision.
3. Eligible forecast origins near the cycle end had no `origin + H` cell for H ≥ 2, which would
   have forced the modeller to fabricate a target. Eligibility now requires room for every
   declared horizon.
4. Several validator checks were themselves wrong (sign of the ladder `diff`, a comparison
   across mismatched indexes, an off-by-one on `total_weeks`) and were corrected rather than
   worked around.
5. `verification.before_decision_window` compared every application against the **intake-1**
   window, flagging 4,521 false positives; it now uses each application's own intake round.

---

## 6. Limitations — read before using this

1. **The data is synthetic.** Every relationship is a property of the documented generator.
   Nothing here evidences real institutional performance.
2. **Attribution is not causation.** Channel and campaign fields are associational. Programme
   mix, cycle mix and applicant composition differ across channels. No causal claim about
   marketing spend is supported.
3. **Irreducible noise is deliberate.** Ability, intent, financial constraint and competing
   offers are latent and only partially observed, so the target cannot be recovered exactly
   even with the true generator parameters. Expect a real performance ceiling.
4. **Two training cycles is thin.** With 4 cycles the split is 2/1/1. A rolling-origin
   backtest within a cycle is possible but the training history is short. Consider
   `--n-cycles 5` or 6 for a firmer fit; this trades against per-cycle sample size.
5. **Leakage risk is a process risk, not a data risk.** The boundary is machine-checked *for the
   declared feature sets*. If you build a new feature outside the allow-lists, you lose that
   check — add it to `admitflow_schema.py` and re-run the validator.
6. **`is_repeat_applicant` (in `fact_applicant`) is a lifetime flag and leaks.** Use
   `is_repeat_applicant_at_prediction` (in `fact_application`), which is the safe version. Both
   exist; only the second is a feature.
7. **No waitlist process.** Admission is a single milestone; a waitlist would change the
   decision semantics materially.
8. **Enrolment is one event.** Registration and the first fee instalment are a single
   timestamp, so a deposit sub-process cannot be modelled.
9. **Scholarship is an offer attribute, not a stage.** It is recorded on the offer, not tracked
   as a separate funnel step.
10. **Apparent seat scarcity is endogenous.** Admit cutoffs tighten as applications-per-seat
    rise, so a capacity variable partly *contains* the outcome. Treat `base_seat_capacity` and
    `demand_weight` as context, not as causal levers.
11. **Panel weeks are calendar weeks, not cohorts.** `cum_enrolled` mixes two intake rounds;
    filter by round if that matters for your question.
12. **The generator is the only ground truth.** There is no external benchmark to calibrate
    against, and the validator can only prove internal consistency, not realism.

### Open questions still needing a decision (T-01 … T-05)

| ID | Question | Blocks |
|---|---|---|
| T-01 | Region granularity — is 8 synthetic regions enough, or is district/pincode needed? | geo segmentation |
| T-02 | Should scholarship be its own funnel stage? | funnel structure |
| T-03 | Should enrolment be split into offer acceptance and fee payment? | offer-acceptance analysis |
| T-04 | Are cross-cycle re-engagement features needed (prior-cycle applicant behaviour)? | feature scope |
| T-05 | Target-cycle holdout vs rolling-origin backtest? | evaluation protocol |

---

## 7. Explicitly not in this deliverable

- No trained model, no hyperparameter search, no model card.
- No accuracy, AUC, precision, recall, RMSE, SHAP value or feature importance.
- No causal inference, uplift or incrementality analysis.
- No vector database, RAG index, embedding store or deep-learning pipeline.
- No cloud, API or microservice component.
- No hand-edited CSV row, and no machine-specific absolute path in any script.

The profiling report contains a single-feature rank-AUC screen. It is a **data-quality check**
proving the target is not trivially predictable, not a model score, and it must not be quoted
as one.
