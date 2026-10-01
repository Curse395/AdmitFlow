# AdmitFlow Dataset Handoff

> **Scope of this document.** This is an audit of what exists in the workspace
> `C:\OpenCode Projects\datasets\admitflow-data` as inspected. Every number below was read
> from the actual generated files or from the actual report files. Nothing was regenerated,
> modified, or re-estimated during this audit.
>
> Where a check was never performed, this document says **"Not calculated"**. Where the
> implementation is genuinely ambiguous or internally inconsistent, it says so explicitly
> rather than smoothing it over.

---

## 1. Dataset Status

| Item | Value | Evidence |
|---|---|---|
| Generation status | **Complete.** 10 raw tables + 1 processed view written. | `data/raw/_manifest.json` records 10 SHA-256 hashes + 1 for the processed view. |
| Validation status | **Complete: 436 checks, 0 FAIL, 0 WARN.** | `reports/validation_report.md` line 7 (overall status) and the per-family summaries. |
| Profiling status | **Complete.** 10 sections rendered. | `reports/profiling_report.md` exists, 28,754 bytes. |
| Overall status | **Dataset foundation complete and internally consistent.** | See §15 for two unresolved inconsistencies found during this audit. |
| Exact dataset filename(s) | `fact_application.csv`, `fact_applicant.csv`, `fact_funnel_event.csv`, `fact_engagement.csv`, `fact_forecast_panel.csv`, `dim_funnel_stage.csv`, `dim_region.csv`, `dim_programme.csv`, `dim_admission_cycle.csv`, `dim_campaign.csv`, `applications_modelling_view.csv` | `data/` listing |
| Exact dataset location(s) | `C:\OpenCode Projects\datasets\admitflow-data\data\raw\` and `C:\OpenCode Projects\datasets\admitflow-data\data\processed\` | filesystem |

The **primary modelling file** is `data/processed/applications_modelling_view.csv`.
The **central fact table** is `data/raw/fact_application.csv` (28,000 × 61).

---

## 2. Dataset Size

All values below were read directly from the CSVs. No estimation.

| Measure | Value |
|---|---|
| `fact_application` | **28,000 rows × 61 columns** — 10,023,052 bytes |
| `fact_applicant` | **25,279 rows × 7 columns** — 1,498,809 bytes |
| `fact_funnel_event` | **84,383 rows × 11 columns** — 8,110,522 bytes |
| `fact_engagement` | **38,369 rows × 12 columns** — 2,844,705 bytes |
| `fact_forecast_panel` | **2,064 rows × 24 columns** — 284,029 bytes |
| `dim_programme` | **12 rows × 12 columns** — 1,365 bytes |
| `dim_admission_cycle` | **4 rows × 20 columns** — 1,195 bytes |
| `dim_campaign` | **32 rows × 9 columns** — 4,065 bytes |
| `dim_region` | **8 rows × 5 columns** — 468 bytes |
| `dim_funnel_stage` | **7 rows × 7 columns** — 1,365 bytes |
| `applications_modelling_view` | **12,161 rows × 58 columns** — 5,297,024 bytes |
| Total rows, all 10 raw tables | **178,158** |
| Unique applicants (`fact_applicant.applicant_id`) | **25,279** |
| Unique applications (`fact_application.application_id`) | **28,000** |
| Admission cycles | **4** (`CYC-2022`, `CYC-2023`, `CYC-2024`, `CYC-2025`) |
| Programmes | **12** (`PGM-01` … `PGM-12`) |
| Regions | **8** (`REG-01` … `REG-08`) |
| Campaigns | **32** (8 per cycle, 4 cycles, all `is_active = True`) |
| Registered fields (10 raw tables) | **168** |
| Registered fields in modelling view | **58** |
| Total registered fields | **226** |

**Applicants holding more than one application: 2,529.** Distribution of
`fact_applicant.application_count`: 1 → 22,750; 2 → 2,337; 3 → 192. Rows are therefore **not
independent** at the applicant level.

---

## 3. Analytical Contract

Final values as actually implemented in the generated data and the schema registry
(`scripts/admitflow_schema.py`). Source: `docs/admitflow_data_contract.md` §B–§F.

| Element | Final implemented value |
|---|---|
| **Admission funnel** | 7 cumulative milestones, prefix-closed, non-re-entrant. `prospect` (1) → `application_started` (2) → `application_submitted` (3) → `application_verified` (4) → `admission_decision` (5) → `admitted` (6) → `enrolled` (7). All 7 rows in `dim_funnel_stage` carry `allows_reentry = False` and `requires_all_prior_stages = True`. |
| **Prediction unit** | **One `application`** — one applicant's journey to one programme in one admission cycle. PK `fact_application.application_id`. Confirmed non-trivial: 25,279 applicants hold 28,000 applications. |
| **Prediction target** | **Primary: `enrolled_flag`** (binary). **Secondary: `enrolled_given_admitted_flag`** (binary, defined only for admits). **Tertiary: `admitted_flag`** (binary, POST_OUTCOME). |
| **Positive class** | `1` — registration completed for this programme in this cycle (`enrolled_flag = 1`). Rate over the modelling view: **0.278596** (3,388 / 12,161). Over all 28,000 applications: **0.121000**. |
| **Prediction point** | **`application_submitted_ts`** (stage 3). The modelling view is restricted to rows with `stage_reached_order >= 3`. Secondary prediction point: `admission_decision_ts`. Both timestamps exist in the data. |
| **Forecasting horizon** | **H ∈ {1, 2, 4, 6} weeks** — stored in `data/raw/_manifest.json` → `config.forecast_horizons_weeks`. Declared in `GeneratorConfig.forecast_horizons_weeks`. All four verified observable at every eligible origin. |
| **Forecast origin** | A `fact_forecast_panel` week where `is_forecast_eligible = True`. **552 eligible origins.** Four conditions (all verified in code): `week_index_in_cycle >= 4`; week starts on/after `intake1_decision_start`; week starts on/after `week_start_date <= cycle_end_date`; and `week_index_in_cycle + H <= total_weeks - 1` for **every** declared H. |
| **Forecast frequency** | **Weekly**, rolling origin, ISO weeks with Monday start (verified: 0 of 2,064 weeks start on a non-Monday). Panel grain = programme × cycle × week. |
| **Forecast target value** | `cum_enrolled` at `origin + H` (cumulative). Weekly increments `wk_applications_submitted`, `wk_applications_verified`, `wk_decisions_issued`, `wk_admitted`, `wk_enrolled` are also present. |
| **Outcome window** | From `application_submitted_ts` to the cycle's registration close. All 4 cycles have `is_finalised = True`; no right-censoring. |

**TBD items** (unresolved by design; carried in the contract as T-01…T-05): region
granularity, scholarship as a separate funnel stage, enrolment/deposit split, cross-cycle
re-engagement features, and target-cycle holdout vs rolling-origin backtest. See §16.

---

## 4. Entity Model

Ten entities, exactly as present in `data/raw/`. Relationships are taken from
`scripts/admitflow_schema.py` → `FOREIGN_KEYS` and were verified (§7).

```
dim_funnel_stage (7)          dim_region (8)          dim_programme (12)
        ^                           ^                        ^
        | stage_code                | region_id              | programme_id
        |                           |                        |
   fact_funnel_event ----+     fact_applicant          dim_admission_cycle (4)
        |  application_id |           | applicant_id          ^  cycle_id
        |                  +-----------+                       |
        +--> fact_application <---------+-----------------------+
              |  programme_id, cycle_id
              +--> fact_engagement   (application_id, cycle_id)
              +--> fact_forecast_panel (programme_id, cycle_id)
              +--> dim_campaign (campaign_id on fact_application; cycle_id on dim_campaign)
```

| Entity | Grain | PK | FKs | Cardinality (actual) |
|---|---|---|---|---|
| `dim_funnel_stage` | one funnel stage | `stage_code` | — | 7 rows |
| `dim_region` | one applicant-origin region | `region_id` | — | 8 rows |
| `dim_programme` | one programme | `programme_id` | `campus_region_id` → `dim_region.region_id` | 12 rows; campus regions used: REG-01, REG-02, REG-03, REG-05 |
| `dim_admission_cycle` | one admission cycle | `cycle_id` | — | 4 rows, `total_weeks = 43` each |
| `dim_campaign` | one campaign | `campaign_id` | `cycle_id` → `dim_admission_cycle.cycle_id` | 32 rows = 8 per cycle |
| `fact_applicant` | one applicant | `applicant_id` | `region_id` → `dim_region.region_id` | 25,279 rows; 1..3 applications each |
| `fact_application` | one application journey | `application_id` | `applicant_id`, `programme_id`, `cycle_id`, `campaign_id` | 28,000 rows — the ML unit |
| `fact_funnel_event` | one stage achievement | `event_id` | `application_id`, `programme_id`, `cycle_id`, `stage_code` | 84,383 rows; every application has ≥1 event, exactly one terminal |
| `fact_engagement` | one application × one activity date | `engagement_id` | `application_id`, `cycle_id` | 38,369 rows across 16,230 applications (2.3641 rows/app) |
| `fact_forecast_panel` | programme × cycle × ISO week | `panel_id` | `programme_id`, `cycle_id` | 2,064 rows = 12 × 4 × 43, complete grid |

**Derived (not an entity):** `applications_modelling_view` — a denormalised join of
`fact_application` + `fact_applicant` + `dim_region` + `dim_programme`, filtered to
`stage_reached_order >= 3`. 12,161 rows × 58 columns. Built by the generator, never hand-edited.

---

## 5. Data Dictionary Summary

226 registered fields: 168 across the 10 raw tables, 58 in the modelling view. Rendered
authoritatively in `docs/data_dictionary.md` (85,796 bytes) from the same registry.
`Availability` values: `pre_submission` = strictly before the prediction point;
`at_prediction_point` = known at/by the prediction point and not changing after;
`post_prediction_point` = determined after the prediction point (**forbidden** as a primary
feature); `not_applicable` = key, target, or reference attribute.

Role totals across raw tables: DERIVED 54, REFERENCE 33, GENERATED 31, KEY 25,
POST_OUTCOME 23, TARGET 2.
Leakage totals: none 110, low 32, high 26.

`Fset` column: `P` = member of the `primary` allow-list, `D` = member of the `decision`
allow-list, `—` = not a feature of either.


#### 5.1 `dim_funnel_stage` — funnel stage reference (7 fields)

| Field | Meaning | Type | Role | Availability at prediction time | Leakage | Fset |
|---|---|---|---|---|---|---|
| `stage_order` | Integer position of the stage in the ladder (1..7). | int64 | REFERENCE | not_applicable | none | — |
| `stage_code` | Stable machine key of the stage. | str | KEY | not_applicable | none | — |
| `stage_name` | Human readable stage name. | str | REFERENCE | not_applicable | none | — |
| `stage_kind` | Whether the stage is a cumulative milestone or a discrete event. | str | REFERENCE | not_applicable | none | — |
| `allows_reentry` | Whether the stage can be re-entered after being left. | bool | REFERENCE | not_applicable | none | — |
| `requires_all_prior_stages` | Whether reaching the stage requires every earlier stage to have been reached. | bool | REFERENCE | not_applicable | none | — |
| `stage_description` | Full definition, entry condition and exit condition of the stage. | str | REFERENCE | not_applicable | none | — |

#### 5.2 `dim_region` — applicant-origin region (5 fields)

| Field | Meaning | Type | Role | Availability at prediction time | Leakage | Fset |
|---|---|---|---|---|---|---|
| `region_id` | Region key. | str | KEY | not_applicable | none | — |
| `region_name` | Fictional region name. | str | REFERENCE | not_applicable | none | — |
| `region_type` | Settlement type of the region. | str | REFERENCE | not_applicable | low | — |
| `mean_distance_km_to_campus` | Mean travel distance from the region to the institution campus; a proxy for r… | float64 | GENERATED | pre_submission | low | — |
| `region_inquiry_weight` | Share of prospects originating in the region. | float64 | GENERATED | pre_submission | low | — |

#### 5.3 `dim_programme` — programme reference (12 fields)

| Field | Meaning | Type | Role | Availability at prediction time | Leakage | Fset |
|---|---|---|---|---|---|---|
| `programme_id` | Programme key. | str | KEY | not_applicable | none | — |
| `programme_name` | Programme name. | str | REFERENCE | not_applicable | none | — |
| `programme_code` | Short programme code. | str | REFERENCE | not_applicable | none | — |
| `faculty` | Faculty the programme belongs to. | str | REFERENCE | not_applicable | none | — |
| `award_level` | Award level of the programme. | str | REFERENCE | not_applicable | none | — |
| `duration_years` | Programme duration in years. | int64 | GENERATED | pre_submission | low | — |
| `annual_fee_inr` | Published annual tuition fee in INR; a driver of offer acceptance through the… | int64 | GENERATED | pre_submission | low | — |
| `base_seat_capacity` | Approved intake capacity for one admission cycle. | int64 | GENERATED | pre_submission | low | — |
| `selectivity_tier` | Published selectivity band. | str | REFERENCE | pre_submission | low | — |
| `review_duration_days` | Median days from submission to document verification. | float64 | GENERATED | pre_submission | low | — |
| `demand_weight` | Relative attractiveness driving how many prospects the programme attracts. | float64 | GENERATED | pre_submission | low | — |
| `campus_region_id` | Region in which the programme is taught. | str | KEY | pre_submission | low | — |

#### 5.4 `dim_admission_cycle` — admission cycle calendar (20 fields)

| Field | Meaning | Type | Role | Availability at prediction time | Leakage | Fset |
|---|---|---|---|---|---|---|
| `cycle_id` | Admission cycle key. | str | KEY | not_applicable | none | — |
| `academic_year_label` | Human readable academic year. | str | REFERENCE | not_applicable | none | — |
| `cycle_start_date` | First day of the cycle (equal to intake 1 application open date). | date | DERIVED | not_applicable | none | — |
| `cycle_end_date` | Last day of the cycle (equal to intake 2 enrolment end date). | date | DERIVED | not_applicable | none | — |
| `intake1_application_open` | Intake 1 applications open. | date | REFERENCE | not_applicable | none | — |
| `intake1_application_close` | Intake 1 application submission deadline. Determines `intake_round` at prospe… | date | REFERENCE | not_applicable | none | — |
| `intake1_decision_start` | First day of the intake 1 decision release window. | date | REFERENCE | not_applicable | none | — |
| `intake1_decision_end` | Last day of the intake 1 decision release window. | date | REFERENCE | not_applicable | none | — |
| `intake1_offer_deadline` | Last date on which an intake 1 offer can be accepted. | date | REFERENCE | not_applicable | none | — |
| `intake1_enrolment_end` | Last date of intake 1 registration and fee payment. | date | REFERENCE | not_applicable | none | — |
| `intake2_application_open` | Intake 2 applications open (day after intake 1 close). | date | REFERENCE | not_applicable | none | — |
| `intake2_application_close` | Intake 2 application submission deadline. | date | REFERENCE | not_applicable | none | — |
| `intake2_decision_start` | First day of the intake 2 decision release window. | date | REFERENCE | not_applicable | none | — |
| `intake2_decision_end` | Last day of the intake 2 decision release window. | date | REFERENCE | not_applicable | none | — |
| `intake2_offer_deadline` | Last date on which an intake 2 offer can be accepted. | date | REFERENCE | not_applicable | none | — |
| `intake2_enrolment_end` | Last date of intake 2 registration and fee payment. | date | REFERENCE | not_applicable | none | — |
| `verification_end_date` | Last day on which document verification may be completed. | date | DERIVED | not_applicable | none | — |
| `total_weeks` | Number of ISO weeks spanned by the cycle; the panel row count per programme-c… | int64 | DERIVED | not_applicable | none | — |
| `is_finalised` | True once all outcomes of the cycle are known. All cycles shipped here are fi… | bool | REFERENCE | not_applicable | none | — |
| `total_seats_offers` | Sum of seat capacity across all programmes in the cycle. | int64 | DERIVED | not_applicable | none | — |

#### 5.5 `dim_campaign` — campaign reference (9 fields)

| Field | Meaning | Type | Role | Availability at prediction time | Leakage | Fset |
|---|---|---|---|---|---|---|
| `campaign_id` | Campaign key. | str | KEY | not_applicable | none | — |
| `campaign_name` | Campaign name. | str | REFERENCE | not_applicable | none | — |
| `channel` | Channel the campaign runs on. | str | REFERENCE | not_applicable | none | — |
| `cycle_id` | Admission cycle the campaign belongs to. | str | KEY | not_applicable | none | — |
| `start_date` | Campaign start date. | date | REFERENCE | pre_submission | none | — |
| `end_date` | Campaign end date. | date | REFERENCE | pre_submission | none | — |
| `planned_budget_inr` | Planned campaign budget in INR. | int64 | GENERATED | pre_submission | none | — |
| `target_group` | Intended audience segment, recorded for slice-based attribution analysis. | str | REFERENCE | not_applicable | none | — |
| `is_active` | Whether the campaign ran to plan. | bool | REFERENCE | not_applicable | none | — |

#### 5.6 `fact_applicant` — one row per applicant (7 fields)

| Field | Meaning | Type | Role | Availability at prediction time | Leakage | Fset |
|---|---|---|---|---|---|---|
| `applicant_id` | Synthetic applicant surrogate key. Carries no external meaning. | str | KEY | not_applicable | none | — |
| `region_id` | Applicant origin region. | str | KEY | pre_submission | low | — |
| `gender_band` | Self-reported gender band, synthetic. Used for programme mix and segmentation… | str | GENERATED | pre_submission | low | — |
| `education_level` | Highest qualification held at the time of the first application. | str | GENERATED | pre_submission | low | — |
| `first_inquiry_date` | Date of the applicant's first ever inquiry. | date | DERIVED | pre_submission | low | — |
| `application_count` | Number of applications held by this applicant across all cycles. | int64 | DERIVED | pre_submission | low | — |
| `is_repeat_applicant` | True if the applicant holds more than one application across their WHOLE hist… | bool | DERIVED | post_prediction_point | high | — |

#### 5.7 `fact_application` — one row per application, the ML unit (61 fields)

| Field | Meaning | Type | Role | Availability at prediction time | Leakage | Fset |
|---|---|---|---|---|---|---|
| `application_id` | Synthetic application surrogate key. One row = one applicant's journey to one… | str | KEY | not_applicable | none | — |
| `applicant_id` | Owning applicant. | str | KEY | not_applicable | none | — |
| `programme_id` | Programme applied to. | str | KEY | pre_submission | low | — |
| `cycle_id` | Admission cycle. | str | KEY | pre_submission | low | — |
| `campaign_id` | Attributed campaign. Null unless the acquisition channel is campaign-bearing. | str | KEY | pre_submission | low | — |
| `acquisition_channel` | First-touch acquisition channel. ASSOCIATION ONLY: differences across channel… | str | GENERATED | pre_submission | low | — |
| `acquisition_source` | Specific source / sub-channel within `acquisition_channel`. | str | GENERATED | pre_submission | low | — |
| `first_touch_date` | Date of the applicant's first recorded marketing touch. Always on or before `… | str | GENERATED | pre_submission | low | — |
| `touchpoints_count` | Number of recorded marketing touchpoints before the inquiry. | int64 | GENERATED | pre_submission | low | — |
| `is_multi_touch` | True if the prospect had more than one touchpoint before inquiring. | bool | GENERATED | pre_submission | low | — |
| `is_referral_alumni` | True if the referral came from an alumnus. | bool | GENERATED | pre_submission | low | — |
| `intake_round` | Intake round this application belongs to, fixed at prospect creation from the… | int64 | GENERATED | pre_submission | low | — |
| `academic_score_pct` | Percentage score on the qualifying examination, as reported at submission. A … | float64 | GENERATED | at_prediction_point | low | — |
| `academic_score_band` | Banded academic score. Derived ONLY from `academic_score_pct`, which is known… | str | DERIVED | at_prediction_point | low | — |
| `doc_completeness_score` | Completeness of the supporting document set as assessed at submission, in [0.… | float64 | GENERATED | at_prediction_point | low | — |
| `fee_scholarship_applied` | True if the applicant applied for fee concession or scholarship at submission… | bool | GENERATED | at_prediction_point | low | — |
| `is_repeat_applicant_at_prediction` | True if, at the moment this application was submitted, the applicant already … | bool | DERIVED | at_prediction_point | low | — |
| `inquiry_ts` | Timestamp of the inquiry that opened this application. Equals the `prospect` … | str | GENERATED | pre_submission | none | — |
| `application_started_ts` | Timestamp of the first form session. Equals the `application_started` funnel … | str | GENERATED | pre_submission | none | — |
| `application_submitted_ts` | Timestamp of submission. Equals the `application_submitted` funnel event time… | str | DERIVED | at_prediction_point | none | — |
| `prediction_ts` | Explicit prediction timestamp for the primary task. Equal to `application_sub… | str | DERIVED | at_prediction_point | none | — |
| `prediction_stage` | Funnel stage at which the primary prediction is made. | str | DERIVED | at_prediction_point | none | — |
| `days_inquiry_to_start` | Days from inquiry to first form session. | int64 | DERIVED | pre_submission | none | — |
| `days_start_to_submit` | Days from first form session to submission. | int64 | DERIVED | at_prediction_point | none | — |
| `days_inquiry_to_submit` | Days from inquiry to submission. The single strongest behavioural summary of … | int64 | DERIVED | at_prediction_point | none | — |
| `days_to_round_close_at_start` | Days remaining from the first form session to the intake round close date. Ca… | int64 | DERIVED | pre_submission | none | — |
| `week_of_cycle_at_submission` | ISO week index of the submission week relative to the cycle start week (0-bas… | int64 | DERIVED | at_prediction_point | none | — |
| `month_of_submission` | Calendar month of submission (1-12). | int64 | DERIVED | at_prediction_point | none | — |
| `pre_sub_session_count` | Total pre-submission sessions in `fact_engagement`. | int64 | DERIVED | pre_submission | none | — |
| `pre_sub_active_days` | Number of distinct pre-submission activity dates. | int64 | DERIVED | pre_submission | none | — |
| `pre_sub_total_minutes` | Total minutes of pre-submission portal activity. | float64 | DERIVED | pre_submission | none | — |
| `pre_sub_doc_uploads` | Documents uploaded before submission. | int64 | DERIVED | pre_submission | none | — |
| `pre_sub_form_fields_completed` | Form fields completed before submission. | int64 | DERIVED | pre_submission | none | — |
| `pre_sub_return_visits` | Pre-submission sessions that were return visits (not the applicant's first se… | int64 | DERIVED | pre_submission | none | — |
| `stage_reached` | Highest funnel stage reached by this application. CONTAINS THE ANSWER - never… | str | POST_OUTCOME | post_prediction_point | high | — |
| `stage_reached_order` | Integer position of `stage_reached`. CONTAINS THE ANSWER - never a feature. | int64 | POST_OUTCOME | post_prediction_point | high | — |
| `dropoff_stage` | Stage at which the application left the funnel. Null when enrolled. | str | POST_OUTCOME | post_prediction_point | high | — |
| `dropoff_reason` | Single categorical reason for leaving the funnel. Null when enrolled. | str | POST_OUTCOME | post_prediction_point | high | — |
| `doc_query_raised` | True if document clarification was requested during verification. | bool | POST_OUTCOME | post_prediction_point | high | — |
| `doc_query_count` | Number of document clarification requests raised. | int64 | POST_OUTCOME | post_prediction_point | high | — |
| `doc_verification_status` | Verification outcome for the application. | str | POST_OUTCOME | post_prediction_point | high | — |
| `application_verified_ts` | Timestamp at which verification was granted. Strictly after submission. | str | POST_OUTCOME | post_prediction_point | high | — |
| `admission_decision_ts` | Timestamp at which the decision was released. | str | POST_OUTCOME | post_prediction_point | high | — |
| `admitted_ts` | Timestamp at which the offer was dispatched and the seat confirmed. Strictly … | str | POST_OUTCOME | post_prediction_point | high | — |
| `enrolled_ts` | Timestamp at which registration and first fee instalment were completed. THE … | str | POST_OUTCOME | post_prediction_point | high | — |
| `days_submitted_to_verified` | Days from submission to verification. | int64 | POST_OUTCOME | post_prediction_point | high | — |
| `days_verified_to_decision` | Days from verification to decision release. | int64 | POST_OUTCOME | post_prediction_point | high | — |
| `days_decision_to_enrolled` | Days from decision to enrolment for admitted applicants. | int64 | POST_OUTCOME | post_prediction_point | high | — |
| `decision_type` | Formal decision released. THE DECISION ITSELF - never a feature. | str | POST_OUTCOME | post_prediction_point | high | — |
| `selection_score` | The institution's internal merit score, computed at decision time from transc… | float64 | POST_OUTCOME | post_prediction_point | high | — |
| `offer_letter_issued` | True if an offer letter was issued. | bool | POST_OUTCOME | post_prediction_point | high | — |
| `offer_deadline` | Last date the offer could be accepted. | str | POST_OUTCOME | post_prediction_point | high | — |
| `scholarship_offered` | True if a fee concession accompanied the offer. | bool | POST_OUTCOME | post_prediction_point | high | — |
| `scholarship_amount_inr` | Annual concession amount in INR. Zero when no scholarship was offered. | int64 | POST_OUTCOME | post_prediction_point | high | — |
| `withdrawn_flag` | True if the applicant withdrew after submission. | bool | POST_OUTCOME | post_prediction_point | high | — |
| `withdrawn_date` | Date of withdrawal. Null when the applicant did not withdraw. | str | POST_OUTCOME | post_prediction_point | high | — |
| `admitted_flag` | 1 if the applicant was admitted. STRUCTURALLY FORBIDDEN as a feature: it is a… | int64 | POST_OUTCOME | post_prediction_point | high | — |
| `enrolled_given_admitted_flag` | Conditional target: 1 if an ADMITTED applicant went on to enrol. Null for app… | int64 | TARGET | post_prediction_point | high | — |
| `enrolled_flag` | PRIMARY TARGET. 1 if the applicant completed registration for this programme … | int64 | TARGET | post_prediction_point | high | — |
| `cohort_label` | Programme x cycle cohort key used for cohort analysis and dashboards. | str | DERIVED | pre_submission | low | — |
| `split_hint` | Chronological split hint derived ONLY from `cycle_id` (earliest cycles train,… | str | DERIVED | pre_submission | low | — |

#### 5.8 `fact_funnel_event` — one row per stage achievement (11 fields)

| Field | Meaning | Type | Role | Availability at prediction time | Leakage | Fset |
|---|---|---|---|---|---|---|
| `event_id` | Funnel event key. | str | KEY | not_applicable | none | — |
| `application_id` | Application the milestone belongs to. | str | KEY | not_applicable | none | — |
| `programme_id` | Denormalised programme (partition/join key). | str | KEY | not_applicable | none | — |
| `cycle_id` | Denormalised admission cycle (partition key). | str | KEY | not_applicable | none | — |
| `stage_code` | Stage achieved. | str | KEY | not_applicable | none | — |
| `stage_order` | Integer ladder position of the stage. | int64 | DERIVED | not_applicable | none | — |
| `intake_round` | Intake round of the owning application. | int64 | DERIVED | not_applicable | none | — |
| `event_ts` | Milestone timestamp. | str | GENERATED | not_applicable | none | — |
| `event_date` | Calendar date of the milestone. | str | DERIVED | not_applicable | none | — |
| `days_since_prev_stage` | Days elapsed since the previous achieved milestone. Null for the first stage. | int64 | DERIVED | not_applicable | none | — |
| `is_terminal_stage` | True for the single highest stage the application reached. | bool | DERIVED | not_applicable | none | — |

#### 5.9 `fact_engagement` — one row per application × activity date (12 fields)

| Field | Meaning | Type | Role | Availability at prediction time | Leakage | Fset |
|---|---|---|---|---|---|---|
| `engagement_id` | Engagement row key. | str | KEY | not_applicable | none | — |
| `application_id` | Application the activity belongs to. | str | KEY | not_applicable | none | — |
| `cycle_id` | Denormalised admission cycle. | str | KEY | not_applicable | none | — |
| `activity_date` | Date of portal activity. Always on or before date(application_submitted_ts) f… | str | GENERATED | not_applicable | none | — |
| `days_before_submission` | Days between the activity and the prediction point. Null when the application… | int64 | DERIVED | not_applicable | none | — |
| `session_count` | Sessions on the activity date. | int64 | GENERATED | not_applicable | none | — |
| `total_minutes` | Minutes of activity on the date. | float64 | GENERATED | not_applicable | none | — |
| `pages_viewed` | Programme pages viewed on the date. | int64 | GENERATED | not_applicable | none | — |
| `docs_uploaded` | Documents uploaded on the date. | int64 | GENERATED | not_applicable | none | — |
| `form_fields_completed` | Form fields completed on the date. | int64 | GENERATED | not_applicable | none | — |
| `device_type` | Dominant device for the day's sessions. | str | GENERATED | not_applicable | none | — |
| `is_return_visit` | True if the day's sessions were a return to the form rather than the first se… | bool | GENERATED | not_applicable | none | — |

#### 5.10 `fact_forecast_panel` — programme × cycle × ISO week (24 fields)

| Field | Meaning | Type | Role | Availability at prediction time | Leakage | Fset |
|---|---|---|---|---|---|---|
| `panel_id` | Panel cell key. | str | KEY | not_applicable | none | — |
| `programme_id` | Programme. | str | KEY | not_applicable | none | — |
| `cycle_id` | Admission cycle. | str | KEY | not_applicable | none | — |
| `week_start_date` | Monday of the ISO week. | str | DERIVED | not_applicable | none | — |
| `week_end_date` | Sunday of the ISO week. | str | DERIVED | not_applicable | none | — |
| `week_index_in_cycle` | 0-based ISO week index from the cycle start week. | int64 | DERIVED | not_applicable | none | — |
| `is_forecast_eligible` | True when this week can serve as a forecast origin for the enrolled-yield tas… | bool | DERIVED | not_applicable | none | — |
| `split_hint` | Chronological split hint derived only from cycle_id. | str | DERIVED | not_applicable | none | — |
| `n_applications` | Number of application rows in the cell's programme-cycle, for denominator che… | int64 | DERIVED | not_applicable | none | — |
| `cum_applications_opened` | Cumulative applications opened (stage `prospect`) as at the end of the week. … | int64 | DERIVED | not_applicable | none | — |
| `cum_applications_started` | Cumulative applications started (stage `application_started`) as at the end o… | int64 | DERIVED | not_applicable | none | — |
| `cum_applications_submitted` | Cumulative applications submitted (stage `application_submitted`) as at the e… | int64 | DERIVED | not_applicable | none | — |
| `cum_applications_verified` | Cumulative applications verified (stage `application_verified`) as at the end… | int64 | DERIVED | not_applicable | none | — |
| `cum_decisions_issued` | Cumulative decisions released (stage `admission_decision`) as at the end of t… | int64 | DERIVED | not_applicable | none | — |
| `cum_admitted` | Cumulative admitted (stage `admitted`) as at the end of the week. Derived: ru… | int64 | DERIVED | not_applicable | none | — |
| `cum_enrolled` | Cumulative enrolled (stage `enrolled`) as at the end of the week. PRIMARY FOR… | int64 | DERIVED | not_applicable | none | — |
| `wk_applications_submitted` | Applications submitted during the week. Derived: count of events whose event_… | int64 | DERIVED | not_applicable | none | — |
| `wk_applications_verified` | Applications verified during the week. Derived: count of events whose event_d… | int64 | DERIVED | not_applicable | none | — |
| `wk_decisions_issued` | Decisions released during the week. Derived: count of events whose event_date… | int64 | DERIVED | not_applicable | none | — |
| `wk_admitted` | Admitted during the week. Derived: count of events whose event_date falls ins… | int64 | DERIVED | not_applicable | none | — |
| `wk_enrolled` | Enrolled during the week. Derived: count of events whose event_date falls ins… | int64 | DERIVED | not_applicable | none | — |
| `cum_submit_to_verify_rate` | cum_applications_verified / cum_applications_submitted. NULL while the denomi… | float64 | DERIVED | not_applicable | none | — |
| `cum_admit_rate` | cum_admitted / cum_decisions_issued. NULL while the denominator is zero. | float64 | DERIVED | not_applicable | none | — |
| `cum_enrolment_yield` | cum_enrolled / cum_applications_submitted. The headline yield metric of the p… | float64 | DERIVED | not_applicable | none | — |

#### 5.11 `applications_modelling_view` — derived modelling view (58 fields)

| Field | Meaning | Type | Role | Availability at prediction time | Leakage | Fset |
|---|---|---|---|---|---|---|
| `application_id` | Synthetic application key. Join key, not a feature. | see source | DERIVED | pre_submission | none | — |
| `applicant_id` | Synthetic applicant key. Join key, not a feature. | see source | DERIVED | pre_submission | none | — |
| `programme_id` | Programme applied to. | see source | DERIVED | pre_submission | none | P/D |
| `cycle_id` | Admission cycle. | see source | DERIVED | pre_submission | none | P/D |
| `cohort_label` | Programme x cycle cohort key. | see source | DERIVED | pre_submission | none | P/D |
| `split_hint` | Chronological split hint from cycle_id only. | see source | DERIVED | pre_submission | none | P/D |
| `acquisition_channel` | First-touch acquisition channel (association only, not causal). | see source | DERIVED | pre_submission | none | P/D |
| `acquisition_source` | Sub-channel within the acquisition channel. | see source | DERIVED | pre_submission | none | P/D |
| `campaign_id` | Attributed campaign, null for non-campaign channels. | see source | DERIVED | pre_submission | none | P/D |
| `first_touch_date` | First recorded marketing touch date. | see source | DERIVED | pre_submission | none | P/D |
| `touchpoints_count` | Marketing touchpoints before inquiry. | see source | DERIVED | pre_submission | none | P/D |
| `is_multi_touch` | More than one pre-inquiry touchpoint. | see source | DERIVED | pre_submission | none | P/D |
| `is_referral_alumni` | Referral originated from an alumnus. | see source | DERIVED | pre_submission | none | P/D |
| `region_id` | Applicant origin region. | see source | DERIVED | pre_submission | none | P/D |
| `region_name` | Region name. | see source | DERIVED | pre_submission | none | P/D |
| `region_type` | Settlement type. | see source | DERIVED | pre_submission | none | P/D |
| `mean_distance_km_to_campus` | Mean travel distance to campus; proxy for relocation cost. | see source | DERIVED | pre_submission | none | P/D |
| `gender_band` | Synthetic gender band. Segmentation only, never a decision variable. | see source | DERIVED | pre_submission | none | P/D |
| `education_level` | Highest qualification held at first application. | see source | DERIVED | pre_submission | none | P/D |
| `is_repeat_applicant_at_prediction` | Applicant already held another submitted application at this prediction point… | see source | DERIVED | pre_submission | none | P/D |
| `selectivity_tier` | Published selectivity band. | see source | DERIVED | pre_submission | none | P/D |
| `duration_years` | Programme duration. | see source | DERIVED | pre_submission | none | P/D |
| `annual_fee_inr` | Published annual fee. | see source | DERIVED | pre_submission | none | P/D |
| `base_seat_capacity` | Approved intake capacity. | see source | DERIVED | pre_submission | none | P/D |
| `review_duration_days` | Median submission-to-verification duration. | see source | DERIVED | pre_submission | none | P/D |
| `demand_weight` | Published relative programme attractiveness. | see source | DERIVED | pre_submission | none | P/D |
| `campus_region_id` | Region of the campus. | see source | DERIVED | pre_submission | none | P/D |
| `intake_round` | Intake round. | see source | DERIVED | pre_submission | none | P/D |
| `academic_score_pct` | Qualifying examination score, reported at submission. | see source | DERIVED | pre_submission | none | P/D |
| `academic_score_band` | Banded academic score (from the submission-time score only). | see source | DERIVED | pre_submission | none | P/D |
| `doc_completeness_score` | Document completeness at submission. | see source | DERIVED | pre_submission | none | P/D |
| `fee_scholarship_applied` | Fee concession applied for at submission. | see source | DERIVED | pre_submission | none | P/D |
| `inquiry_ts` | Inquiry timestamp. | see source | DERIVED | pre_submission | none | P/D |
| `application_started_ts` | First form session timestamp. | see source | DERIVED | pre_submission | none | P/D |
| `application_submitted_ts` | Submission timestamp. THE PREDICTION POINT. | see source | DERIVED | pre_submission | none | P/D |
| `days_inquiry_to_start` | Days from inquiry to first session. | see source | DERIVED | pre_submission | none | P/D |
| `days_start_to_submit` | Days from first session to submission. | see source | DERIVED | pre_submission | none | P/D |
| `days_inquiry_to_submit` | Days from inquiry to submission. | see source | DERIVED | pre_submission | none | P/D |
| `days_to_round_close_at_start` | Days from first session to the round close date. | see source | DERIVED | pre_submission | none | P/D |
| `week_of_cycle_at_submission` | ISO week index of submission within the cycle. | see source | DERIVED | pre_submission | none | P/D |
| `month_of_submission` | Calendar month of submission. | see source | DERIVED | pre_submission | none | P/D |
| `pre_sub_session_count` | Pre-submission sessions. | see source | DERIVED | pre_submission | none | P/D |
| `pre_sub_active_days` | Distinct pre-submission activity dates. | see source | DERIVED | pre_submission | none | P/D |
| `pre_sub_total_minutes` | Pre-submission activity minutes. | see source | DERIVED | pre_submission | none | P/D |
| `pre_sub_doc_uploads` | Documents uploaded pre-submission. | see source | DERIVED | pre_submission | none | P/D |
| `pre_sub_form_fields_completed` | Form fields completed pre-submission. | see source | DERIVED | pre_submission | none | P/D |
| `pre_sub_return_visits` | Pre-submission return visits. | see source | DERIVED | pre_submission | none | P/D |
| `admission_decision_ts` | Decision timestamp. It is the PREDICTION POINT of the secondary decision view… | see source | DERIVED | pre_submission | none | — |
| `application_verified_ts` | Verification timestamp. NOT a primary feature; available at the decision poin… | see source | DERIVED | pre_submission | none | /D |
| `doc_verification_status` | Verification outcome. NOT a primary feature; available at the decision point. | see source | DERIVED | pre_submission | none | /D |
| `doc_query_raised` | Document query raised. NOT a primary feature; available at the decision point. | see source | DERIVED | pre_submission | none | /D |
| `doc_query_count` | Document query count. NOT a primary feature; available at the decision point. | see source | DERIVED | pre_submission | none | /D |
| `days_submitted_to_verified` | Submission-to-verification days. NOT a primary feature; known at the decision… | see source | DERIVED | pre_submission | none | /D |
| `stage_reached` | Highest stage reached. POST_OUTCOME. | see source | DERIVED | pre_submission | none | — |
| `stage_reached_order` | Ladder position of stage_reached. POST_OUTCOME. | see source | DERIVED | pre_submission | none | — |
| `admitted_flag` | Secondary target for admission-offer prediction. POST_OUTCOME, never a featur… | see source | DERIVED | pre_submission | none | — |
| `enrolled_given_admitted_flag` | Conditional secondary target, predicted at the decision point. | see source | DERIVED | pre_submission | none | — |
| `enrolled_flag` | PRIMARY TARGET. Registration completed for this programme in this cycle. | see source | DERIVED | pre_submission | none | — |

#### 5.12 Field/column presence check

| Table | Declared in registry | Columns in CSV | Declared but absent | In CSV but undeclared |
|---|---|---|---|---|
| `dim_funnel_stage` | 7 | 7 | — | — |
| `dim_region` | 5 | 5 | — | — |
| `dim_programme` | 12 | 12 | — | — |
| `dim_admission_cycle` | 20 | 20 | — | — |
| `dim_campaign` | 9 | 9 | — | — |
| `fact_applicant` | 7 | 7 | — | — |
| `fact_application` | 61 | 61 | — | — |
| `fact_funnel_event` | 11 | 11 | — | — |
| `fact_engagement` | 12 | 12 | — | — |
| `fact_forecast_panel` | 24 | 24 | — | — |
| `applications_modelling_view` | 58 | 58 | — | — |
| **Total** | **226** | **226** | | |

**Registry-to-CSV conformance is exact for all 11 files: 0 declared fields missing and 0 undeclared columns.** The `primary`/`decision` allow-lists reference `region_inquiry_weight` (in `dim_region`) and `application_count` (in `fact_applicant`), which exist in raw but are not carried into the modelling view — see §15.1(b).

---

## 6. Funnel Validation

All figures recomputed from `fact_application.csv` and `fact_funnel_event.csv` during this
audit. They match `reports/profiling_report.md` §6.

### 6.1 Stage counts and conversion

| # | Stage | Cumulative reached | Step conversion | Top-of-funnel | Cumulative drop-off | Cumulative drop-off % |
|---|---|---|---|---|---|---|
| 1 | `prospect` | 28,000 | — | 1.000000 | 0 | 0.000000 |
| 2 | `application_started` | 16,230 | 0.579643 | 0.579643 | 11,770 | 0.420357 |
| 3 | `application_submitted` | 12,161 | 0.749291 | 0.434321 | 15,839 | 0.565679 |
| 4 | `application_verified` | 10,023 | 0.824192 | 0.357964 | 17,977 | 0.642036 |
| 5 | `admission_decision` | 9,854 | 0.983139 | 0.351929 | 18,146 | 0.648071 |
| 6 | `admitted` | 4,727 | 0.479704 | 0.168821 | 23,273 | 0.831179 |
| 7 | `enrolled` | 3,388 | 0.716734 | **0.121000** | 24,612 | 0.879000 |

### 6.2 Drop-off reasons (actual counts and share of that stage's exits)

| Stage | Reason | Count | Share of stage exits |
|---|---|---|---|
| `prospect` | `no_response` | 5,863 | 0.4981 |
| `prospect` | `browsed_only` | 4,052 | 0.3443 |
| `prospect` | `enquiry_closed_unqualified` | 1,855 | 0.1576 |
| `application_started` | `form_abandoned` | 1,841 | 0.4524 |
| `application_started` | `deadline_missed` | 1,464 | 0.3598 |
| `application_started` | `requirements_unclear` | 764 | 0.1878 |
| `application_submitted` | `incomplete_documents` | 1,579 | 0.7385 |
| `application_submitted` | `ineligible_qualification` | 559 | 0.2615 |
| `application_verified` | `withdrawn_by_applicant` | 96 | 0.5680 |
| `application_verified` | `accepted_elsewhere_withdrawn` | 73 | 0.4320 |
| `admission_decision` | `below_merit_cutoff` | 3,621 | 0.7063 |
| `admission_decision` | `eligibility_criteria_failed` | 971 | 0.1894 |
| `admission_decision` | `capacity_exhausted` | 535 | 0.1043 |
| `admitted` | `offer_not_accepted` | 371 | 0.2771 |
| `admitted` | `chose_other_institution` | 362 | 0.2704 |
| `admitted` | `offer_deadline_lapsed` | 356 | 0.2659 |
| `admitted` | `financial_constraint` | 250 | 0.1867 |

Total drop-offs: **24,612** (= 28,000 − 3,388). Reasons are stage-specific and weighted, not
uniform. `dropoff_stage` uses 6 of the 7 declared stage codes — `enrolled` never appears,
which is correct (enrolled rows have `dropoff_stage = NULL`). `dropoff_reason` uses 17 of 18
declared values.

### 6.3 Structural invariants — actual violation counts

| Invariant | Violations |
|---|---|
| F1 — prefix-closed staircase (no stage skipped) | **0** |
| F1 — at most one milestone per (application, stage) | **0** duplicates |
| F2 — milestone timestamps strictly increase along the ladder | **0** |
| F3 — exactly one terminal milestone per application | **0** |
| F3 — every application present in `fact_funnel_event` | **0** (28,000 of 28,000) |
| F4 — cumulative counters non-increasing down the panel ladder | **0** of 2,064 cells |
| F5 — drop-off reasons within declared domain | **0** invalid |

### 6.4 Impossible transitions — actual violation counts

| Check | Violations |
|---|---|
| Admitted (`stage_reached_order >= 6`) with `decision_type != 'admit'` | 0 |
| Admitted without `admission_decision_ts` | 0 |
| `enrolled_flag = 1` at a stage other than 7 | 0 |
| `enrolled_flag = 1` without `admitted_flag = 1` | 0 |
| `enrolled_given_admitted_flag` set where `admitted_flag != 1` | 0 |
| Withdrawn application that still received a decision | 0 |
| `decision_type = 'admit'` without `admitted_ts` | 0 |
| Reached verification without `application_verified_ts` | 0 |
| `scholarship_amount_inr > 0` without `scholarship_offered` | 0 |
| `offer_letter_issued != (decision_type == 'admit')` | 0 |

**Funnel validation failures: 0.**

### 6.5 Chronological violations

| Check | Violations |
|---|---|
| Non-increasing milestone timestamps (F2) | 0 |
| Panel ladder decreasing (F4) | 0 |
| Panel week not starting on Monday | 0 |
| Panel `week_index_in_cycle` + 1 ≠ `total_weeks` at the last cell of any programme-cycle | 0 |
| Panel ↔ `fact_application` enrolled reconciliation mismatch | 0 |
| Panel ↔ `fact_application` submitted reconciliation mismatch | 0 |
| `n_applications` ≠ final `cum_applications_opened` | 0 |

**Chronological violations: 0.**

---

## 7. Data Quality Validation

### 7.1 Duplicate records and primary keys

| Table | Primary key | Duplicate keys | Fully duplicated rows |
|---|---|---|---|
| `dim_funnel_stage` | `stage_code` | 0 | 0 |
| `dim_region` | `region_id` | 0 | 0 |
| `dim_programme` | `programme_id` | 0 | 0 |
| `dim_admission_cycle` | `cycle_id` | 0 | 0 |
| `dim_campaign` | `campaign_id` | 0 | 0 |
| `fact_applicant` | `applicant_id` | 0 | 0 |
| `fact_application` | `application_id` | 0 | 0 |
| `fact_funnel_event` | `event_id` | 0 | 0 |
| `fact_engagement` | `engagement_id` | 0 | 0 |
| `fact_forecast_panel` | `panel_id` | 0 | 0 |
| `applications_modelling_view` | `application_id` | 0 | — |

**Duplicates: 0 across all 11 files.**

### 7.2 Referential integrity — all 15 declared foreign keys

**Orphan values: 0 on every one of the 15 FK relationships.** Verified:

`dim_programme.campus_region_id`→`dim_region.region_id` · `dim_campaign.cycle_id`→`dim_admission_cycle.cycle_id` ·
`fact_applicant.region_id`→`dim_region.region_id` · `fact_application.applicant_id`→`fact_applicant.applicant_id` ·
`fact_application.programme_id`→`dim_programme.programme_id` · `fact_application.cycle_id`→`dim_admission_cycle.cycle_id` ·
`fact_application.campaign_id`→`dim_campaign.campaign_id` · `fact_funnel_event.application_id`→`fact_application.application_id` ·
`fact_funnel_event.programme_id`→`dim_programme.programme_id` · `fact_funnel_event.cycle_id`→`dim_admission_cycle.cycle_id` ·
`fact_funnel_event.stage_code`→`dim_funnel_stage.stage_code` · `fact_engagement.application_id`→`fact_application.application_id` ·
`fact_engagement.cycle_id`→`dim_admission_cycle.cycle_id` · `fact_forecast_panel.programme_id`→`dim_programme.programme_id` ·
`fact_forecast_panel.cycle_id`→`dim_admission_cycle.cycle_id`.

### 7.3 Missing values — exact counts

Five tables have **zero** nulls: `dim_funnel_stage`, `dim_region`, `dim_programme`,
`dim_admission_cycle`, `dim_campaign`, `fact_applicant`.

All nulls in `fact_application.csv` are **declared** (`nullable = True` in the registry):

| Column | Nulls | % | Role | Null population |
|---|---|---|---|---|
| `application_submitted_ts`, `prediction_ts`, `prediction_stage`, `academic_score_pct`, `academic_score_band`, `doc_completeness_score`, `days_start_to_submit`, `days_inquiry_to_submit`, `week_of_cycle_at_submission`, `month_of_submission`, `pre_sub_session_count`, `pre_sub_active_days`, `pre_sub_total_minutes`, `pre_sub_doc_uploads`, `pre_sub_form_fields_completed`, `pre_sub_return_visits` | 15,839 each | 0.565679 | mixed | never reached stage 3 |
| `application_started_ts`, `days_inquiry_to_start`, `days_to_round_close_at_start` | 11,770 each | 0.420357 | mixed | never reached stage 2 |
| `campaign_id` | 15,595 | 0.556964 | KEY | non-campaign channel |
| `dropoff_stage`, `dropoff_reason` | 3,388 each | 0.121000 | POST_OUTCOME | enrolled (correct) |
| `application_verified_ts`, `days_submitted_to_verified` | 17,977 each | 0.642036 | POST_OUTCOME | never reached stage 4 |
| `admission_decision_ts`, `decision_type`, `selection_score`, `days_verified_to_decision` | 18,146 each | 0.648071 | POST_OUTCOME | never reached stage 5 |
| `admitted_ts`, `offer_deadline`, `enrolled_given_admitted_flag` | 23,273 each | 0.831179 | POST_OUTCOME / TARGET | never admitted |
| `enrolled_ts`, `days_decision_to_enrolled` | 24,612 each | 0.879000 | POST_OUTCOME | never enrolled |
| `withdrawn_date` | 27,831 | 0.993964 | POST_OUTCOME | did not withdraw |

Other tables: `fact_funnel_event.days_since_prev_stage` 28,000 null (0.331820 — first milestone
has no predecessor); `fact_engagement.days_before_submission` 10,487 null (0.273320);
`fact_forecast_panel.cum_admit_rate` 1,218 null (0.590116), `cum_submit_to_verify_rate` and
`cum_enrolment_yield` 192 null each (0.093023) — all zero-denominator cases.

**Unexpected nulls: 0.** The null pattern matches the funnel exactly: the 15,839 rows with no
submission timestamp are precisely the rows that did not reach `application_submitted`.

Modelling view nulls: `campaign_id` 7,307; `admission_decision_ts` 2,307;
`application_verified_ts` 2,138; `days_submitted_to_verified` 2,138;
`enrolled_given_admitted_flag` 7,434. All 53 other columns are fully populated.

### 7.4 Invalid categories

**Invalid values: 0** across all 20 columns with a declared domain. Declared-vs-observed:

| Column | Declared | Observed | Invalid |
|---|---|---|---|
| `dim_funnel_stage.stage_code` | 7 | 7 | 0 |
| `dim_funnel_stage.stage_kind` | 2 | 1 (`CUMULATIVE_MILESTONE`) | 0 |
| `dim_region.region_type` | 4 | 4 | 0 |
| `dim_programme.faculty` | 5 | 5 | 0 |
| `dim_programme.award_level` | 1 | 1 (`UG`) | 0 |
| `dim_programme.selectivity_tier` | 3 | 3 | 0 |
| `dim_campaign.channel` | 8 | 4 | 0 |
| `dim_campaign.target_group` | 4 | 4 | 0 |
| `fact_applicant.gender_band` | 3 | 3 | 0 |
| `fact_applicant.education_level` | 4 | 4 | 0 |
| `fact_application.acquisition_channel` | 8 | 8 | 0 |
| `fact_application.acquisition_source` | 27 | 27 | 0 |
| `fact_application.academic_score_band` | 5 | 5 | 0 |
| `fact_application.prediction_stage` | 1 | 1 | 0 |
| `fact_application.stage_reached` | 7 | 7 | 0 |
| `fact_application.dropoff_stage` | 7 | 6 | 0 |
| `fact_application.dropoff_reason` | 18 | 17 | 0 |
| `fact_application.doc_verification_status` | 4 | 4 | 0 |
| `fact_application.decision_type` | 2 | 2 | 0 |
| `fact_application.split_hint` | 3 | 3 | 0 |
| `fact_funnel_event.stage_code` | 7 | 7 | 0 |
| `fact_engagement.device_type` | 3 | 3 | 0 |
| `fact_forecast_panel.split_hint` | 3 | 3 | 0 |

Under-observed domains are all by design, not defects: `stage_kind` has one funnel shape;
`award_level` is UG-only; `dim_campaign` only covers the 4 campaign-bearing channels; and
`enrolled` / one drop-off reason never occur as outcomes.

### 7.5 Invalid numerical values

**Out-of-range values: 0** on every checked field.

| Column | Min | Max | Out of range |
|---|---|---|---|
| `academic_score_pct` | 40.0 | 99.0 | 0 (expected 0–100) |
| `doc_completeness_score` | 0.15 | 1.0 | 0 (expected 0–1) |
| `touchpoints_count` | 1 | 12 | 0 (expected 1–12) |
| `selection_score` | 0.0 | 100.0 | 0 (expected 0–100) |
| `intake_round` | 1 | 2 | 0 (expected 1–2) |
| `enrolled_flag` | 0 | 1 | 0 non-binary |
| `admitted_flag` | 0 | 1 | 0 non-binary |
| `enrolled_given_admitted_flag` | 0 | 1 | 0 non-binary |
| `pre_sub_session_count` | 1 | 16 | 0 negative |
| `pre_sub_active_days` | 1 | 8 | 0 negative |
| `pre_sub_total_minutes` | 1.0 | 411.5 | 0 negative |
| `pre_sub_doc_uploads` | 0 | 10 | 0 negative |
| `pre_sub_form_fields_completed` | 0 | 42 | 0 negative |
| `pre_sub_return_visits` | 0 | 7 | 0 negative |
| `scholarship_amount_inr` | 0 | 107,500 | no negative |

### 7.6 Invalid dates

**Invalid or impossible dates: 0** on the checks performed. Verified: no engagement row occurs
after its application's prediction point (0 violations); all 2,064 panel weeks are 7 days
starting Monday; cycle windows are ordered; every `intake_round` submission falls on or before
its round close date (validator check `submission.within_round_close`, PASS); every enrolment
falls inside its round's registration window (PASS); no enrolment occurs after the offer
deadline (PASS).

### 7.7 Data quality summary

| Category | Result |
|---|---|
| Missing values | 0 unexpected; all nulls declared and explained by the funnel |
| Duplicate records | 0 |
| Duplicate primary keys | 0 |
| Invalid categories | 0 |
| Invalid numerical values | 0 |
| Invalid dates | 0 |
| Referential-integrity failures | 0 of 15 FKs |

---

## 8. ML/Leakage Validation

An actual machine check was performed, not merely a documentation claim. Evidence:
`reports/validation_report.md`, family `ML`, 104 checks, all PASS.

### 8.1 Target distribution

| Target | Population | n | Positives | Negatives | Positive rate |
|---|---|---|---|---|---|
| `enrolled_flag` (primary) | modelling view, submitted applications | 12,161 | 3,388 | 8,773 | **0.278596** |
| `admitted_flag` (tertiary) | modelling view | 12,161 | 4,727 | 7,434 | 0.388702 |
| `enrolled_given_admitted_flag` (secondary) | admits only | 4,727 | 3,388 | 1,339 | 0.716734 |
| `enrolled_flag` | all applications | 28,000 | 3,388 | 24,612 | 0.121000 |

### 8.2 Potential leakage fields — 26 fields flagged `leakage = high`

All are `POST_OUTCOME` or `TARGET` in `fact_application.csv`:

`stage_reached`, `stage_reached_order`, `dropoff_stage`, `dropoff_reason`, `doc_query_raised`,
`doc_query_count`, `doc_verification_status`, `application_verified_ts`,
`admission_decision_ts`, `admitted_ts`, `enrolled_ts`, `days_submitted_to_verified`,
`days_verified_to_decision`, `days_decision_to_enrolled`, `decision_type`, `selection_score`,
`offer_letter_issued`, `offer_deadline`, `scholarship_offered`, `scholarship_amount_inr`,
`withdrawn_flag`, `withdrawn_date`, `admitted_flag`, `enrolled_given_admitted_flag`,
`enrolled_flag` — plus `enrolled_given_admitted_flag` and `enrolled_flag` as `TARGET`.

`selection_score` (the institution's internal merit score) is **deliberately retained** in the
raw table as a trap, per decision D-11.

### 8.3 Features excluded because of leakage

| Check | Result |
|---|---|
| `leakage.no_post_outcome_in_primary_features` | **PASS** — none of the 45 `primary` features is POST_OUTCOME or TARGET |
| `leakage.no_post_outcome_in_decision_features` | **PASS** — none of the 45 `decision` features is POST_OUTCOME or TARGET |
| `leakage.modelling_view_primary_clean` | **PASS** — modelling view exposes no POST_OUTCOME field as a primary feature |
| `leakage.selection_score_excluded` | **PASS** — `selection_score` absent from the modelling view |
| `leakage.boundary[primary].*` (per column, vs `application_submitted_ts`) | **PASS** on every checked column — source timestamp ≤ prediction point on every row |
| `leakage.boundary[decision].*` (per column, vs `admission_decision_ts`) | **PASS** on every checked column |
| `leakage.duplicate_of_target[*]` | **PASS** — no feature is an exact copy of the target |

`is_repeat_applicant` on `fact_applicant` is a **lifetime** flag (rate 0.100044) and is
classified high-risk. The safe version `fact_application.is_repeat_applicant_at_prediction`
(rate 0.018036) is the one in the `primary` feature set.

### 8.4 Suspiciously predictive fields

An actual single-feature rank-AUC screen was run against `enrolled_flag`.

**Safe primary features (41 present in the modelling view), top 8:**

| Feature | Rank AUC |
|---|---|
| `doc_completeness_score` | 0.713 |
| `academic_score_pct` | 0.706 |
| `academic_score_band` | 0.628 |
| `annual_fee_inr` | 0.627 |
| `programme_id` | 0.618 |
| `campus_region_id` | 0.597 |
| `demand_weight` | 0.592 |
| `review_duration_days` | 0.587 |

**Post-outcome columns (excluded by construction), top 5:** `doc_verification_status` 0.622,
`days_submitted_to_verified` 0.565, `doc_query_raised` 0.556, `doc_query_count` 0.548,
`region_type` 0.505. None separates the target perfectly.

### 8.5 Is the target trivially predictable?

**No.** Validator check `target.not_trivially_predictable` is **PASS**: the strongest single
safe feature reaches rank AUC **0.713** against a 0.93 failure threshold. No feature is a copy
of the target, and no post-outcome column separates it perfectly. The residual is irreducible
by construction — latent ability, intent, financial constraint and competing-offer factors are
only partially observed.

### 8.6 Temporal split readiness

**Chronological splitting is possible and pre-assigned.** `split_hint` is a pure function of
`cycle_id` (verified — one value per cycle, no cycle mixed).

| Cycle | `split_hint` | Applications | Submitted | Enrolled | Enrol yield (all apps) |
|---|---|---|---|---|---|
| `CYC-2022` | train | 7,035 | 3,134 | 935 | 0.132907 |
| `CYC-2023` | train | 6,965 | 3,020 | 864 | 0.124049 |
| `CYC-2024` | validation | 7,081 | 3,006 | 800 | 0.112978 |
| `CYC-2025` | test | 6,919 | 3,001 | 789 | 0.114034 |

Modelling view by split: train 6,154 (enrolled 0.29233, admitted 0.40559); validation 3,006
(enrolled 0.26613, admitted 0.37026); test 3,001 (enrolled 0.26291, admitted 0.37254).

**Caveat:** only 2 training cycles. Also, because applicants can hold up to 3 applications
(2,529 do), a naive random split would leak across `applicant_id`. Use `split_hint`, or group
folds by `applicant_id` if you re-split.

---

## 9. Temporal Coverage

| Measure | Value |
|---|---|
| Earliest `inquiry_ts` | **2022-06-10 17:12:00** |
| Earliest funnel event | 2022-06-10 17:12:00 |
| Earliest `application_submitted_ts` | 2022-06-17 04:12:00 |
| Latest `enrolled_ts` | **2026-02-26 06:25:58** |
| Latest funnel event | 2026-02-26 06:25:58 |
| Total span | **44 months** |
| Admission cycles | 4, all with `is_finalised = True` |

### Cycle calendar as stored in `dim_admission_cycle`

| Cycle | Academic year | Window | Weeks | Intake 1 open → close → decision | Intake 2 open → close → decision | Enrolment end |
|---|---|---|---|---|---|---|
| `CYC-2022` | AY2022-23 | 2022-06-01 → 2023-03-20 | 43 | 06-01 → 10-15 → 11-20 | 10-16 → 12-20 → 2023-01-15 | 2023-03-20 |
| `CYC-2023` | AY2023-24 | 2023-06-01 → 2024-03-20 | 43 | 06-01 → 10-15 → 11-20 | 10-16 → 12-20 → 2024-01-15 | 2024-03-20 |
| `CYC-2024` | AY2024-25 | 2024-06-01 → 2025-03-20 | 43 | 06-01 → 10-15 → 11-20 | 10-16 → 12-20 → 2025-01-15 | 2025-03-20 |
| `CYC-2025` | AY2025-26 | 2025-06-01 → 2026-03-20 | 43 | 06-01 → 10-15 → 11-20 | 10-16 → 12-20 → 2026-01-15 | 2026-03-20 |

Submission windows: CYC-2022 2022-06-17→2022-12-20 · CYC-2023 2023-06-17→2023-12-20 ·
CYC-2024 2024-06-20→2024-12-20 · CYC-2025 2025-06-22→2025-12-20.

Intake round split: intake 1 = 11,873, intake 2 = 16,127 (both rounds present in every cycle).

**Chronological train/validation/test splitting: possible, and already assigned** via
`split_hint` (2 train / 1 validation / 1 test). Forecast origins: **552 eligible** of 2,064
panel cells; H = 1, 2, 4 and 6 weeks all verified observable at every eligible origin.

---

## 10. Attribution

Attribution fields present in `fact_application`: `acquisition_channel` (8 values),
`acquisition_source` (27 values), `campaign_id`, `first_touch_date`, `touchpoints_count`,
`is_multi_touch`, `is_referral_alumni`. All are first-touch recorded association.

### `acquisition_channel` — counts, submit rate, enrolment yield (all applications)

| Channel | Applications | Share | Submit rate (≥ stage 3) | Enrol yield |
|---|---|---|---|---|
| `organic_search` | 5,562 | 0.198643 | 0.487055 | 0.136282 |
| `paid_search` | 4,966 | 0.177357 | 0.391865 | 0.106726 |
| `social_media` | 3,791 | 0.135393 | 0.361646 | 0.091533 |
| `referral` | 2,981 | 0.106464 | 0.529353 | 0.149950 |
| `email_campaign` | 2,980 | 0.106429 | 0.441611 | 0.124161 |
| `direct` | 2,674 | 0.095500 | 0.455871 | 0.128646 |
| `education_fair` | 2,533 | 0.090464 | 0.428741 | 0.121595 |
| `partner_agency` | 2,513 | 0.089750 | 0.372463 | 0.113012 |

### `acquisition_source` — all 27 values

`meta_ads_prospect` 1,707 · `google_ads_brand` 1,635 · `google_ads_generic` 1,624 ·
`content_blog` 1,421 · `bing_organic` 1,398 · `programme_page` 1,384 · `google_organic` 1,359 ·
`newsletter_prospectus` 1,007 · `alumni_referral_mail` 991 · `linkedin_organic` 990 ·
`open_day_invite` 982 · `meta_ads_retarget` 965 · `youtube_organic` 920 · `instagram_organic` 916 ·
`app_download` 908 · `direct_web` 886 · `walk_in` 880 · `district_career_fair` 879 ·
`nri_helpdesk` 852 · `college_career_fair` 844 · `education_consultant` 833 ·
`overseas_counsellor` 828 · `school_fair` 810 · `school_counsellor` 787 · `alumni_referral` 752 ·
`peer_referral` 726 · `parent_referral` 716.

### Campaign attribution

- `campaign_id` populated on **12,405** rows (0.443036); null on **15,595** (0.556964).
- `dim_campaign` holds 32 campaigns — 8 per cycle, covering only the 4 campaign-bearing channels
  (`email_campaign`, `paid_search`, `partner_agency`, `social_media` × 8 each). All 32
  `is_active = True`.
- Consistency: **0** rows carry a `campaign_id` on a non-campaign channel.
- **1,845** rows sit on a campaign-bearing channel with a **null** `campaign_id`. This is
  consistent with the declared design ("null unless the acquisition channel is campaign-bearing
  *and* a campaign was matched"), but it means channel and campaign are not interchangeable —
  1,845 rows are campaign-channel applications with no campaign match. Flagging rather than
  treating it as an error.

### Other touch fields

- `touchpoints_count`: 1→3,352; 2→6,456; 3→6,845; 4→5,204; 5→3,228; 6→1,690; 7→761; 8→307;
  9→92; 10→45; 11→16; 12→4. Range 1–12.
- `is_multi_touch` rate: 0.880286.
- `is_referral_alumni` rate: 0.029214.

**Causal interpretation: not supported.** These are association fields. Programme mix, cycle
mix and applicant composition differ across channels, so the yield spread above is confounded.
Nothing in this dataset supports a claim that any channel caused any outcome.

---

## 11. Programme/Cohort Coverage

### 11.1 Programmes (12) — from `dim_programme`

| ID | Name | Faculty | Tier | Fee (INR) | Seats | Years | Campus region |
|---|---|---|---|---|---|---|---|
| `PGM-01` | B.Sc. Data Science | Science | high | 195,500 | 90 | 4 | REG-01 |
| `PGM-02` | B.Sc. Computer Science | Technology | high | 167,500 | 120 | 4 | REG-01 |
| `PGM-03` | B.Sc. Information Technology | Technology | medium | 122,000 | 90 | 3 | REG-02 |
| `PGM-04` | B.Sc. Mathematics | Science | medium | 123,000 | 60 | 3 | REG-01 |
| `PGM-05` | B.Sc. Biotechnology | Science | high | 159,000 | 60 | 3 | REG-01 |
| `PGM-06` | B.Sc. Physics | Science | medium | 106,000 | 45 | 3 | REG-01 |
| `PGM-07` | B.Com (Hons.) | Commerce | emerging | 101,000 | 150 | 3 | REG-02 |
| `PGM-08` | BBA | Management | medium | 117,000 | 120 | 3 | REG-02 |
| `PGM-09` | BCA | Technology | emerging | 97,500 | 90 | 3 | REG-02 |
| `PGM-10` | B.A. Economics | Humanities | emerging | 74,000 | 60 | 3 | REG-03 |
| `PGM-11` | B.Sc. Food Technology | Science | emerging | 143,000 | 45 | 3 | REG-05 |
| `PGM-12` | B.Com (Taxation & Finance) | Commerce | emerging | 78,000 | 75 | 3 | REG-03 |

All 12 are `award_level = UG`, across 5 faculties, 3 selectivity tiers.

### 11.2 Programme volumes and conversion

| Programme | Applications | Submitted | Enrolled | Submit rate | Enrol yield |
|---|---|---|---|---|---|
| `PGM-01` | 3,682 | 1,584 | 263 | 0.430201 | 0.071429 |
| `PGM-02` | 4,432 | 1,910 | 291 | 0.430957 | 0.065659 |
| `PGM-03` | 3,147 | 1,381 | 361 | 0.438831 | 0.114712 |
| `PGM-04` | 1,475 | 656 | 202 | 0.444746 | 0.136949 |
| `PGM-05` | 1,813 | 815 | 135 | 0.449531 | 0.074462 |
| `PGM-06` | 1,054 | 448 | 182 | 0.425047 | 0.172676 |
| `PGM-07` | 3,343 | 1,448 | 588 | 0.433144 | 0.175890 |
| `PGM-08` | 2,753 | 1,232 | 301 | 0.447512 | 0.109335 |
| `PGM-09` | 2,650 | 1,130 | 464 | 0.426415 | 0.175094 |
| `PGM-10` | 1,435 | 603 | 218 | 0.420209 | 0.151916 |
| `PGM-11` | 860 | 369 | 158 | 0.429070 | 0.183721 |
| `PGM-12` | 1,356 | 585 | 225 | 0.431416 | 0.165929 |

Enrol yield ranges 0.065659–0.183721 (sd 0.0453) — a 2.8× spread, so programme identity
carries real signal. Programme volume ranges 860–4,432.

### 11.3 Cohorts

- `cohort_label` is present on `fact_application` **and** in the modelling view.
- **48 distinct cohorts** = 12 programmes × 4 cycles (e.g. `BA-EC-CYC-2022`, `BBA-CYC-2023`).
  No collisions observed.
- Cohort sizes: min 194, max 1,213, mean 583.33.
- Each cohort maps to exactly **one** `split_hint` (max distinct splits per cohort = 1), so
  cohorts never straddle a split boundary — no cohort leakage into the chronological split.

### 11.4 Regions (8)

| ID | Name | Type | Mean dist. (km) | Inquiry weight | Applicants |
|---|---|---|---|---|---|
| `REG-01` | Metro North | metro | 185.996 | 0.217840 | 6,045 |
| `REG-02` | Metro East | metro | 241.119 | 0.176862 | 4,731 |
| `REG-03` | Coastal South | tier2 | 653.422 | 0.148648 | 3,797 |
| `REG-04` | Highland West | tier2 | 779.379 | 0.125352 | 3,085 |
| `REG-05` | Central Plains | tier3 | 725.749 | 0.105318 | 2,488 |
| `REG-06` | Eastern Belt | tier3 | 630.707 | 0.090348 | 2,090 |
| `REG-07` | Desert Fringe | rural_remote | 1,083.878 | 0.076712 | 1,761 |
| `REG-08` | Hill Tracts | rural_remote | 1,301.549 | 0.058919 | 1,282 |

Note: `region_id` is a **property of the applicant**, not the application, so per-cycle
application counts by region are not directly available from `dim_region`.

---

## 12. Reproducibility

| Item | Value |
|---|---|
| Generator script | `scripts/generate_dataset.py` |
| Validation script | `scripts/validate_dataset.py` |
| Profiling script | `scripts/profile_dataset.py` |
| Schema registry (single source of truth) | `scripts/admitflow_schema.py` |
| Random seed | **20240817** — recorded in `data/raw/_manifest.json` → `config.seed` and in `GeneratorConfig.seed` |
| Configuration mechanism | `GeneratorConfig` dataclass, overridable by CLI flags, serialised into `data/raw/_manifest.json` under `config`. Output root is a parameter (`--root`), default = parent of `scripts/`. **No machine-specific path is hardcoded in any script.** |
| Environment recorded | Python object versions: numpy **2.2.6**, pandas **2.3.3**; `dataset_version` 1.0.0 |
| Integrity mechanism | SHA-256 per output file in `data/raw/_manifest.json` |

**Full recorded config:** `n_applications=28000`, `n_cycles=4`, `start_cycle_year=2022`,
`seed=20240817`, `min_history_weeks=4`, `min_applications_per_cell=60`,
`max_applications_per_applicant=3`, `reuse_prob_same_cycle=0.11`,
`reuse_prob_previous_cycle=0.025`, `forecast_horizons_weeks=[1,2,4,6]`, `float_format=%.6f`,
`dataset_version=1.0.0`.

### Exact commands used to generate

```powershell
cd "C:\OpenCode Projects\datasets\admitflow-data"
python scripts/generate_dataset.py --n-applications 28000 --emit-data-dictionary
```

### Exact commands used to validate

```powershell
python scripts/validate_dataset.py
# and the strict form:
python scripts/validate_dataset.py --fail-on warn
```

### Exact commands used to profile

```powershell
python scripts/profile_dataset.py
```

### Reproducibility verification performed earlier in this project

Two consecutive generator runs at the same seed produced a **byte-identical**
`data/raw/_manifest.json`, i.e. identical SHA-256 for all 11 outputs. This was verified
during dataset construction and is recorded in `docs/dataset_handoff_report.md` §5.

**Note:** re-running the generator or the validator/profile scripts **overwrites** the CSVs,
`docs/data_dictionary.md`, and the two report files. This audit did not re-run them; it read
the existing artefacts and recomputed statistics directly from the CSVs.

---

## 13. Generated Files

Complete list of files created by this work, relative to
`C:\OpenCode Projects\datasets\admitflow-data`. **24 files** (23 produced by the dataset
build, plus this handoff document).

| Directory | Files |
|---|---|
| `docs/` | 4 (this file included) |
| `reports/` | 2 |
| `scripts/` | 4 |
| `data/raw/` | 11 (10 tables + `_manifest.json`) |
| `data/processed/` | 1 |
| project root | 2 (`README.md`, `requirements.txt`) |
| **Total** | **24** |

### Documentation (`docs/`, 4)
| Path | Bytes |
|---|---|
| `docs/admitflow_data_contract.md` | 33,020 |
| `docs/data_dictionary.md` | 85,796 |
| `docs/dataset_handoff_report.md` | 15,653 |
| `docs/ADMITFLOW_DATASET_HANDOFF.md` | this file |

### Reports (`reports/`, 2)
| Path | Bytes |
|---|---|
| `reports/validation_report.md` | 48,227 |
| `reports/profiling_report.md` | 28,754 |

### Scripts (`scripts/`, 4)
| Path | Bytes |
|---|---|
| `scripts/admitflow_schema.py` | 97,611 |
| `scripts/generate_dataset.py` | 67,337 |
| `scripts/validate_dataset.py` | 55,387 |
| `scripts/profile_dataset.py` | 26,785 |

### Data (`data/raw/`, 11 including manifest)
| Path | Bytes |
|---|---|
| `data/raw/fact_application.csv` | 10,023,052 |
| `data/raw/fact_funnel_event.csv` | 8,110,522 |
| `data/raw/fact_applicant.csv` | 1,498,809 |
| `data/raw/fact_engagement.csv` | 2,844,705 |
| `data/raw/fact_forecast_panel.csv` | 284,029 |
| `data/raw/dim_campaign.csv` | 4,065 |
| `data/raw/dim_funnel_stage.csv` | 1,365 |
| `data/raw/dim_programme.csv` | 1,365 |
| `data/raw/dim_admission_cycle.csv` | 1,195 |
| `data/raw/dim_region.csv` | 468 |
| `data/raw/_manifest.json` | 2,848 |

### Processed (`data/processed/`, 1)
| Path | Bytes |
|---|---|
| `data/processed/applications_modelling_view.csv` | 5,297,024 |

### Project root (2)
| Path | Bytes |
|---|---|
| `README.md` | 8,279 |
| `requirements.txt` | 491 |

`requirements.txt` declares only `numpy>=1.24,<3` and `pandas>=2.0,<3`. No ML, plotting,
notebook, database or cloud dependency.

---

## 14. Validation Reports

| Report | Path | Conclusion |
|---|---|---|
| Validation | `reports/validation_report.md` (48,227 bytes) | **436 checks — 0 FAIL, 0 WARN.** Families: STRUCTURAL 153, DATA 92, FUNNEL 33, TEMPORAL 38, ML 104, REALISM 16. Exit code 0 under both `--fail-on fail` and `--fail-on warn`. |
| Profiling | `reports/profiling_report.md` (28,754 bytes) | 10 descriptive sections: shape/inventory, missingness, duplicates + FK integrity, category distributions, target distribution, funnel counts/conversion, programme-cycle-channel conversion, numeric summaries, temporal coverage, synthetic-data fidelity. Contains **no model performance figures** by design. |

### Validation conclusion in detail

The strongest single safe feature reaches rank AUC 0.713 against a 0.93 failure threshold, so
`target.not_trivially_predictable` passes. The leakage boundary is machine-verified against the
data rather than asserted: for every column in a feature set, the validator parses the column's
source timestamp and confirms it is not later than the prediction point. Panel cumulative counts
reconcile exactly with `fact_application` (0 mismatches on both enrolled and submitted), so the
panel can be used for scenario simulation without re-derivation. All four forecast horizons are
confirmed observable at all 552 eligible origins.

### Profiling conclusion in detail

Full ladder retention is 0.121 of prospects. `enrolled_flag` is 0.278596 over the modelling
view. Enrolment yield varies 0.065659–0.183721 across programmes and 0.091533–0.149950 across
channels. Temporal coverage is 44 months across 4 fully closed cycles. The report explicitly
states its single rank-AUC screen is a data-quality check, not a model score.

---

## 15. Known Limitations

Only limitations actually supported by the inspected files and data.

### 15.1 Two unresolved inconsistencies found during this audit

These were **not** previously documented and are reported rather than corrected.

**(a) Admit count exceeds declared seat capacity by 4.7×.**
`dim_admission_cycle.total_seats_offers = 1005` for every cycle (4,020 total), and
`dim_programme.base_seat_capacity` sums to exactly 1,005. But actual admits are **4,727**
(per cycle: 1,289 / 1,207 / 1,113 / 1,118) — a ratio of **4.7035** admits per declared seat.
The admit simulation evidently uses a *relative* merit cutoff rather than a hard seat cap, so
`total_seats_offers` and `base_seat_capacity` are **not enforced as capacity constraints in the
generated data**. Consequence: do not use `base_seat_capacity` or `total_seats_offers` as a
capacity ceiling, and do not present `admitted_flag` counts as "seats filled". Both are safe as
*relative context* features, which is how the contract classifies them (leakage = low).

**(b) Two declared features are absent from the modelling view (43/45).**
`region_inquiry_weight` (from `dim_region`) and `application_count` (from `fact_applicant`) are
registered in both feature-set allow-lists, and **both source columns do exist** in the raw
tables, but neither is carried into `applications_modelling_view.csv`. The validator reports
this as PASS because it only counts (43/45), so the gap is not flagged as a failure. A
modeller using the allow-list will get a `KeyError` on those two names. Recover them by joining
`dim_region.region_inquiry_weight` and `fact_applicant.application_count` onto
`application_id`.

### 15.2 Documented scope limitations

1. **The data is synthetic.** Every relationship is a property of the documented generator.
   No real institution, applicant, or admission outcome is represented.
2. **Attribution is not causal.** Channel/campaign fields are associational; the observed yield
   spread is confounded by programme and cycle mix.
3. **Rows are not independent at applicant level.** 2,529 applicants hold more than one
   application (max 3). A random split will leak; use `split_hint` or group by `applicant_id`.
4. **Only 2 training cycles.** The chronological split is 2/1/1, which is thin for a
   rolling-origin backtest.
5. **No waitlist process.** Admission is a single milestone; `enrolled` follows `admitted`
   directly. There is no `waitlisted` stage in `dim_funnel_stage`.
6. **Enrolment is one event.** Registration and first fee instalment share a single
   `enrolled_ts`; a deposit sub-process cannot be modelled.
7. **Scholarship is an offer attribute, not a stage.** Recorded via `scholarship_offered` and
   `scholarship_amount_inr` on the offer.
8. **1,845 campaign-channel applications have a null `campaign_id`.** Channel and campaign are
   not interchangeable coverage.
9. **`selection_score` is present in raw data.** It is a deliberate leakage trap (D-11). It must
   never enter a feature set. Do not "discover" it and use it.
10. **`fact_applicant.is_repeat_applicant` is a lifetime flag and leaks.** Use
    `fact_application.is_repeat_applicant_at_prediction` (0.018036) instead.
11. **`dim_funnel_stage.stage_kind` declares 2 values but only 1 is used**
    (`CUMULATIVE_MILESTONE`), and `dim_programme.award_level` declares 1 (`UG`). The domains
    are broader than the data; this is intentional headroom, not a defect.
12. **Panel weeks are calendar weeks and mix both intake rounds.** `cum_enrolled` per programme
    × cycle aggregates intake 1 and intake 2; filter by round if that distinction matters.
13. **The generator is the only ground truth.** The validator proves internal consistency, not
    realism. There is no external benchmark to calibrate against.
14. **No model was trained and no performance figure exists anywhere in this deliverable.**
    Accuracy, AUC, precision, recall and RMSE are **Not calculated**.

---

## 16. Important Decisions

Design decisions another developer must know before building the pipeline.

| # | Decision | Consequence for you |
|---|---|---|
| D-01 | Prediction unit is the **application**, not the applicant | Rows are correlated; group by `applicant_id` if you re-split. |
| D-02 | **No waitlist stage.** Admission is one milestone | `enrolled` follows `admitted` directly; 0.479704 admit→enrol step. |
| D-03 | **Enrolment is a single milestone** (registration + first instalment) | No deposit sub-funnel to analyse. |
| D-04 | **Scholarship is an offer attribute**, not a stage | Use `scholarship_offered` / `scholarship_amount_inr` as offer attributes. |
| D-05 | Feature sets are **allow-lists**, not block-lists | 45 declared per set; 2 are not in the modelling view (§15.1b). |
| D-06 | Safe features are separated from post-outcome by **`availability` + `leakage`**, both machine-checked | The validator re-parses each source timestamp against the data. |
| D-07 | `selection_score` is **retained in raw as a trap** (D-11 in the contract) | Its presence is intentional; exclude it. |
| D-08 | `is_repeat_applicant_at_prediction` added as the safe alternative to the leaking lifetime flag | Use the `_at_prediction` version. |
| D-09 | **Two intake rounds per cycle** (1,1873 / 16,127 applications) | A single round would produce a non-forecastable step function. |
| D-10 | Forecast origin eligibility requires **room for every declared H** | 552 eligible origins; origin+H is always a real cell. |
| D-11 | `split_hint` is a **pure function of `cycle_id`** | Never randomise; cohorts never straddle a split. |
| D-12 | Stage-conditional columns are declared `nullable` and their null pattern is **verified against the funnel** | Null ≠ defect. `submission_ts` null means "never submitted". |
| D-13 | Two bugs were found by the validator and fixed in the **generator**, never in the CSVs: `application_started_ts` was never written (100% null), and 80 applications had `decision_ts == admitted_ts` breaking F2 | Data is generated, never hand-patched. |
| D-14 | Four of the validator's own checks were wrong and were corrected, not worked around (ladder `diff` sign, mismatched-index comparison, `total_weeks` off-by-one, intake-1 vs intake-round window) | Recorded so the 0-FAIL result is trustworthy. |
| D-15 | Latent factors (ability, intent, constraint, competing offer) are **only partially observed** | Guarantees irreducible target noise; there is a real performance ceiling. |
| D-16 | Demand crowding is **endogenous** — merit cutoffs tighten as applications-per-seat rise | Capacity variables partly contain the outcome; treat as context, not a causal lever. |

**Ambiguous / TBD — a decision is still required from the project owner:**

| ID | Question | Blocks |
|---|---|---|
| T-01 | Is 8-region granularity sufficient, or is district/pincode needed? | Geo segmentation |
| T-02 | Should scholarship become its own funnel stage? | Funnel structure |
| T-03 | Should enrolment split into offer acceptance and fee payment? | Offer-acceptance analysis |
| T-04 | Are cross-cycle re-engagement features needed? | Feature scope |
| T-05 | Target-cycle holdout vs rolling-origin backtest? | Evaluation protocol |

**Ambiguous, unresolved in code:** the relationship between `base_seat_capacity` /
`total_seats_offers` and the actual admit count (§15.1a). It is not documented whether seat
capacity was *intended* to be a hard constraint that the generator failed to enforce, or is
purely a relative-weights feature. **This needs an explicit decision before any capacity-based
analysis.**

---

## 17. Next Recommended Project Step

**Build and evaluate the primary baseline model on `applications_modelling_view.csv`, using the
pre-assigned chronological `split_hint`.**

Concretely, the next agent should:

1. Join the two missing declared features (§15.1b) or drop them from the allow-list explicitly —
   and decide the seat-capacity question (§15.1a) first, since it affects whether
   `base_seat_capacity` stays in the feature set.
2. Load `data/processed/applications_modelling_view.csv`, take features **only** from the
   `primary` allow-list in `scripts/admitflow_schema.py`, target `enrolled_flag`.
3. Train on `split_hint == 'train'` (6,154 rows), tune on `validation` (3,006), report once on
   `test` (3,001). Group any resampling by `applicant_id`.
4. Establish the leakage baseline first: deliberately fit a model **with** `selection_score`
   and `admitted_flag`, record the inflated score, then report the clean-feature score. This
   demonstrates the leakage boundary works and gives the project a concrete artefact for it.
5. Only then move to the secondary decision task, and separately to the
   `fact_forecast_panel` scenario-simulation work (552 origins, H ∈ {1,2,4,6}).

Prerequisites before that: the T-01…T-05 decisions and the seat-capacity ambiguity in §16.

**This step was not started.** No model was trained, tuned or scored in this deliverable.

---

## 18. Integrity Statement

> The dataset is synthetic and was generated according to the documented AdmitFlow
> specification for development, experimentation, evaluation, and demonstration. It does not
> represent real institutional admissions data.

Supporting facts for this statement, as verified in the workspace:

- `data/raw/_manifest.json` carries `"synthetic": true` and the fictuality notice verbatim.
- All identifiers (`APP…`, `APL…`, `PGM…`, `REG…`, `CYC…`, `CMP…`) are generated by
  `scripts/generate_dataset.py`. No real applicant, institution, campaign or admission outcome
  is represented, and no external dataset was copied.
- No model was trained and **no performance metric of any kind is reported**. Model accuracy,
  AUC, precision, recall and RMSE are **Not calculated**.
- Any metric later computed on this data is a property of the documented generator assumptions
  and must never be presented as real institutional performance.
- The two inconsistencies in §15.1 are disclosed rather than corrected; the dataset was not
  modified during this audit.
