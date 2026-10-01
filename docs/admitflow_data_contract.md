# AdmitFlow — Analytical Data Contract

**Project:** AdmitFlow
**Capstone topic:** Admission Conversion Forecasting with Funnel Attribution and Scenario Simulation
**Document version:** 1.0
**Owner role:** Dataset Engineering Agent
**Status:** Binding contract for the synthetic dataset. The generator MUST obey this document.

> **SYNTHETIC DATA NOTICE**
> The primary project dataset is synthetic and was generated according to the documented AdmitFlow
> admission-funnel specification for development, experimentation, evaluation, and demonstration.
> It does not represent any real institution, applicant, programme, or admission outcome. No model
> result on this dataset may be presented as real-world institutional performance.

---

## 0. Decision log (ambiguities resolved and TBD items)

Nothing in this contract is a silent assumption. Every non-obvious choice is listed here with the
reason it was made, or marked `TBD` with the decision that is still owed.

| # | Decision point | Resolution | Rationale |
|---|---|---|---|
| D-01 | Number of funnel stages | 7 milestones (see §2) | Balances granularity for funnel analytics against event sparsity. |
| D-02 | Waitlist as a separate decision state | **Excluded (deliberate simplification)** | A waitlist state requires a second resolution mechanism and a second "waitlist→admit" sub-funnel, which roughly doubles the funnel validation surface without serving any of the target tasks. `decision_type ∈ {admit, reject}`. Documented as a known simplification (see §L-09). |
| D-03 | Prediction unit | **Application** (§3) | An applicant can hold several applications; an applicant-grain target would be ambiguous. |
| D-04 | Primary target | `enrolled_flag` at application grain (§4) | Full-journey outcome, aligned with the capstone topic "admission conversion". |
| D-05 | Prediction point | `application_submitted_ts` (§5) | The earliest moment at which the application is a real, scoreable object; forces genuine multi-stage reasoning. |
| D-06 | Second target | `enrolled_given_admitted_flag` (§4.3) | Conditional yield task, supports the "offer-acceptance yield" storyline and the scenario engine. |
| D-07 | Third target | `admitted_flag` (§4.4) | Admission-offer prediction. Classified POST_OUTCOME so it can never be a feature of the primary target. |
| D-08 | Forecast panel grain | programme × admission_cycle × ISO week (§6) | Matches how an admissions team reviews yield. |
| D-09 | Forecast target | Cumulative `enrolled_count` at origin + H weeks (§6.4) | Cumulative yield curves are what stakeholders forecast; increments are trivially zero most weeks. |
| D-10 | Single vs multi-intake cycle | **Two intake rounds per cycle** (§6.2) | A single decision round produces a step function that is not forecastable at weekly frequency. Two rounds produce a realistic, staggered, continuous yield curve. |
| D-11 | `selection_score` retained in raw data | **Yes, deliberately** (§8.4) | It is the most realistic leakage trap an admissions dataset contains. The validator must flag it if it appears in a feature set. |
| D-12 | PII | **None.** No names, emails, phones, addresses, DOB, national IDs. | Synthetic data must not carry realistic PII shapes. |
| D-13 | Gender band | **Retained**, synthetic, segmentation only | Useful for programme mix and dashboard segmentation. Explicitly non-causal, not used as a protected-attribute decision variable in this dataset. |
| D-14 | Academic score | **Retained**, one per application | Realistic primary driver of admission. Kept partially noisy so it cannot deterministically recover the target. |
| D-15 | Attribution semantics | **Association only** (§7) | First-touch and assisted-touch fields are recorded for comparison. They are not causal effects. No causal claim is licensed. |

### Open items marked TBD

| # | TBD item | Decision required before it can be resolved |
|---|---|---|
| T-01 | Geographic granularity of `dim_region` | The dataset ships 8 synthetic regions. If the capstone dashboard needs state/district maps, a `geo_level` extension and a richer region table are required. **Owner decision needed.** |
| T-02 | Scholarship sub-process modelling | Scholarship is generated as an attribute of an admitted offer. If the capstone needs a scholarship-application funnel, a separate pre-admission stage and target are required. **Owner decision needed.** |
| T-03 | Fee-payment sub-process | `enrolled` collapses registration + fee payment into one milestone. If a "deposit paid vs balance paid" split is required, `enrolled` must be split into two stages. **Owner decision needed.** |
| T-04 | Backfill / re-applicant across cycles | Cross-cycle re-application is allowed but is not modelled as a deliberate CRM campaign. If a re-engagement feature set is wanted, an explicit `prior_cycle` linkage feature is required. **Owner decision needed.** |
| T-05 | Target cycle holdout | The last cycle is the test cycle by construction. If the project needs a rolling-origin backtest instead, `split_hint` should be retired in favour of a generated `origin_week` index. **Owner decision needed.** |

---

## A. Admission funnel

### A.1 Stage ladder

| Order | Stage code | Stage name | Definition | Entry condition | Exit condition | Cumulative or event | Re-entry / backtracking |
|---|---|---|---|---|---|---|---|
| 1 | `prospect` | Prospect / inquiry | A lead record for a prospective applicant exists, raised by marketing, walk-in, partner or self-initiated enquiry against a named programme and admission cycle. | Lead captured with programme + cycle. | Prospect either starts an application, or is closed as lost. | **Cumulative milestone** (once achieved, always true). | No re-entry. The record is never deleted, only closed. |
| 2 | `application_started` | Application started | The applicant begins the online application form for that programme/cycle. | Prospect record exists; applicant opened the form. | Application submitted before the round close date, or abandoned. | **Cumulative milestone.** | **Re-entry allowed at the session level only.** Re-opening the form is recorded as an engagement day, not as a second `application_started` milestone. The milestone timestamp is the *first* session. |
| 3 | `application_submitted` | Application submitted | A complete-enough application payload is submitted before the applicable intake round's close date. This is the **prediction point**. | `application_started` achieved; payload submitted. | Application is verified, or fails verification, or is withdrawn. | **Cumulative milestone.** | **No backtracking.** A submitted application is never returned to `application_started`. |
| 4 | `application_verified` | Application verified | Registration records, transcripts and identity documents have been received and checked as complete and eligibility-checked. | `application_submitted` achieved. | A decision is released, or verification fails, or the applicant withdraws. | **Cumulative milestone.** | **No backtracking**, but it contains an internal loop: a `doc_query_raised` event may require correction before verification is granted. The loop is *inside* the stage; it does not move the milestone backwards. |
| 5 | `admission_decision` | Decision released | A formal, dated decision (`admit` or `reject`) is released to the applicant. | `application_verified` achieved; applicant not withdrawn. | Decision communicated; no further funnel movement for rejects. | **Cumulative milestone.** | No re-entry. One decision per application, ever. |
| 6 | `admitted` | Admitted | Admission is confirmed: a seat is allotted and the offer is accepted / conditions cleared. | Decision is `admit`. | Applicant enrols, or the offer lapses / is declined. | **Cumulative milestone.** | No re-entry. |
| 7 | `enrolled` | Enrolled | Registration is completed and the first instalment is recorded. **Primary target milestone.** | `admitted` achieved before the offer-accept deadline. | Terminal. | **Cumulative milestone.** | No re-entry. |

### A.2 Conversion and drop-off definitions

Let `S_i ∈ {prospect, application_started, application_submitted, application_verified,
admission_decision, admitted, enrolled}` be the **highest stage reached** by application `i`, and
`ord(S_i)` its integer order (1–7).

- **Stage conversion rate (step k → k+1)**
  `C_k = |{i : ord(S_i) ≥ k+1}| / |{i : ord(S_i) ≥ k}|`
  Denominator is the *cohort that reached stage k*, i.e. it is a true step conversion, not a
  cohort-from-top conversion.
- **Cohort (top-of-funnel) conversion**
  `Cum_k = |{i : ord(S_i) ≥ k}| / |{i}|` where `|{i}|` is all applications in the slice.
- **Drop-off count at stage k** = `|{i : ord(S_i) = k}|`
- **Drop-off reason** is a single categorical label attached to every application that does not
  reach `enrolled`. Applications reaching `enrolled` have a null drop-off stage and reason.

Invariants the generator and validator MUST enforce:

- **F1 — Staircase:** `funnel_events` contains at most one row per `(application_id, stage_code)`
  and, for a given application, the set of achieved stage codes is a **prefix-closed** set:
  `achieved = {prospect, …, S_i}` with no gaps. Skipping a stage is impossible.
- **F2 — Monotone chronology:** `event_ts(stage_1) < event_ts(stage_2) < … < event_ts(S_i)`.
  Strictly increasing, not merely non-decreasing.
- **F3 — Terminal stage:** `is_last_reached_stage = 1` for exactly one event row per application.
- **F4 — Stage containment:** every `event_ts` lies inside the owning cycle's
  `[application_open_date, enrolment_end_date]` window, and inside the owning intake round's
  submission window where the stage requires it.
- **F5 — Drop-off consistency:** `dropoff_stage == S_i` and `dropoff_reason` is non-null whenever
  `S_i != enrolled`.

### A.3 Intakes

Each admission cycle runs **two intake rounds**. `intake_round` is assigned once, at prospect
creation, from the inquiry date relative to the round-1 application close date. An application
belonging to round *r* MUST be submitted on or before `intake{r}_application_close`. Late starters
therefore experience a compressed submission window — this is a deliberate, documented mechanism
that creates realistic "deadline pressure" behaviour.

---

## B. Prediction unit

**Selected unit: `application`** — one row per applicant's application journey to one programme
within one admission cycle. Primary key `application_id`.

### B.1 Why application and not the alternatives

| Candidate | Why it was rejected / accepted |
|---|---|
| **applicant** | Rejected. An applicant may hold several applications (different programmes, different cycles). "Conversion" at applicant grain is ambiguous — admitted to *any* programme, or the *first* one? — and rows are not independent, which breaks naive cross-validation and inflates apparent skill. Applicant remains a first-class entity for cohort and region analysis, but it is not the modelling unit. |
| **application** | **Selected.** It is the atom the admissions CRM actually operates on, it has exactly one terminal outcome, it is the natural join key to `funnel_events` and `engagement`, and it is the only grain at which "conversion" is unambiguous (this application resulted in an enrolment: yes/no). |
| **cohort (programme × cycle)** | Rejected as the classification unit; it is the right unit for **forecasting** (§F) and for programme comparison. With 12 programmes × 4 cycles = 48 cohorts, it is far too coarse for supervised classification. |
| **programme-cycle** | Same as cohort. Adopted only as the panel aggregation level in the forecasting task. |

### B.2 Secondary unit

`fact_forecast_panel` uses **programme × admission_cycle × ISO week** as its row grain, for the
forecasting and scenario tasks. The relationship between the two units is:

`fact_application` (1 row) → contributes to exactly one `(programme_id, cycle_id, week)` cell of the
cumulative funnel in `fact_forecast_panel`, for every stage it reaches.

---

## C. Prediction target

### C.1 Primary target

| Property | Value |
|---|---|
| **Target name** | `enrolled_flag` |
| **Entity / grain** | `fact_application`, one row per `application_id` |
| **Meaning** | 1 if the applicant completed registration for this programme in this cycle within the outcome window; 0 otherwise |
| **Positive class** | `1` — stage `enrolled` reached |
| **Negative class** | `0` — every other outcome: never started, never submitted, verification failed, withdrawn, rejected, admitted but not enrolled, offer lapsed |
| **Prediction point** | `application_submitted_ts` (`prediction_ts`) |
| **Outcome window** | From `prediction_ts` to `cycle.enrolment_end_date` (approximately 4–7 months, varying by intake round) |
| **Modelling view** | The primary ML view is restricted to applications that reached `application_submitted` (§C.5) |

### C.2 Rationale

`enrolled_flag` is the only outcome that a stakeholder actually acts on: a seat that is not
enrolled is a lost seat, a lost fee, and an over-estimate of demand. It is also a **strict
superset** of `admitted_flag`, so a model for it must implicitly reason about the whole funnel
(verification throughput, offer capacity, offer acceptance), which is exactly the capstone's
"funnel attribution" story.

### C.3 Secondary target — conditional yield

| Property | Value |
|---|---|
| **Target name** | `enrolled_given_admitted_flag` |
| **Populated for** | Applications that reached stage `admitted`; null otherwise |
| **Positive class** | 1 — the admitted applicant went on to enrol |
| **Negative class** | 0 — admitted but did not enrol (declined, chose another institution, financial constraint, deadline lapse) |
| **Prediction point** | `admission_decision_ts` |
| **Feature set** | `decision` feature set (§E.3) |
| **Why** | Isolates the offer-acceptance decision, which is the lever a scenario engine would pull (deposit amount, deadline extension, scholarship). |

### C.4 Tertiary target — admission probability

`admitted_flag` is stored and usable as a supervised target for an admission-offer model. It is
classified **POST_OUTCOME** in the data dictionary, which makes it structurally impossible for it to
enter the feature set of the primary or secondary targets. It is a target, never a feature.

### C.5 The modelling view and the row filter

The raw `fact_application` table covers the **entire journey**, including prospects that never
started. Those rows have no `application_submitted_ts` and therefore no prediction point.

The primary ML task is defined on the deterministic view:

```
modelling view = fact_application  WHERE  stage_reached_order >= 3   (reached application_submitted)
```

This filter is part of the contract, not an implementation detail. It is materialised as
`data/processed/applications_modelling_view.csv` by the generator. No target or metric may be
computed on the raw table without stating which view it used.

---

## D. Prediction-time information boundary

**The rule:** a field is a *safe feature* for a target only if, in the raw data, the latest moment
at which the field's content was known is **not after** the prediction timestamp.

Formally, for prediction point `P` and feature `f` with a declared source timestamp field
`src(f)`:

```
f is SAFE  ⟺  src(f)(row) ≤ P(row)   for every row in the modelling view
```

- Primary view: `P = prediction_ts = application_submitted_ts`
- Decision view: `P = admission_decision_ts`

Every column in the data dictionary declares its `source timestamp field`, and the validator
evaluates the inequality **against the actual generated data**, not against documentation claims.
The `fact_engagement` table is filtered to `activity_date ≤ date(prediction_ts)`; the
pre-submission engagement summary columns are therefore safe by construction.

### D.1 What "future" means here

The model must not see the fact that verification will fail, that a decision will be negative,
that an offer will be made, or that the applicant will accept. Since the prediction point is
submission, the entire post-submission funnel is out of bounds. This is a deliberately hard
setting: the model must predict verification pass, admission, and acceptance jointly.

---

## E. Forecasting horizon and forecast origin

### E.1 Forecast task (T-F)

| Property | Value |
|---|---|
| **Unit** | programme × admission_cycle (aggregated weekly) |
| **Frequency** | Weekly, ISO weeks, Monday start |
| **Forecast origin `T`** | Any eligible week start date, rolling weekly within the cycle |
| **Horizon `H`** | 1, 2, 4, 6 weeks (H ∈ {1, 2, 4, 6}) |
| **Actual quantity** | `cum_enrolled` observed at week `T + H` in `fact_forecast_panel` |
| **Predicted quantity** | `cum_enrolled_hat(programme, cycle, T, H)` |
| **Aggregation level** | Cumulative from the start of the cycle (yield curve), not weekly increment |
| **Minimum history** | 4 weeks of panel history before an origin is eligible |
| **Targets also available** | `cum_applications_submitted`, `cum_applications_verified`, `cum_admitted`, and the derived rates `cum_admit_rate`, `cum_enrolment_yield` |

### E.2 Why cumulative

A weekly increment of `enrolled_count` is zero in the large majority of weeks, which makes naive
time-series evaluation meaningless. Cumulative yield is monotone, non-stationary in level but
well-behaved in first difference, and is the quantity stakeholders actually forecast ("how many
enrolled will we have by 15 February?").

### E.3 Prediction-time boundaries for the forecasting task

Forecasting features are the panel history strictly up to and including week `T` plus the
programme/cycle dimension attributes. Any panel value for week `> T` is post-origin information and
is excluded by construction (a rolling-origin feature builder must slice, never look ahead). The
panel itself contains no forward-looking columns.

### E.4 Feature-set contract

Two feature sets are defined. Both are **allow-lists**, not deny-lists: a field is a feature only
if the data dictionary explicitly places it in the set.

| Set | Population | Prediction point | Permitted source timestamps |
|---|---|---|---|
| `primary` | applications that reached `application_submitted` | `application_submitted_ts` | `first_touch_date`, `inquiry_ts`, `application_started_ts`, `application_submitted_ts` |
| `decision` | applications that reached `admission_decision` | `admission_decision_ts` | as `primary`, plus `application_verified_ts` and earlier |

Every other column is either a key, a target, or POST_OUTCOME.

### E.5 Chronological evaluation

`split_hint` is a deterministic function of `cycle_id` (earliest cycles = train, latest = test),
never of the target. With four cycles: cycles 1–2 → `train`, cycle 3 → `validation`, cycle 4 →
`test`. Rolling-origin backtesting within a cycle is the alternative; see T-05.

---

## F. Forecast origin detail

Origins are the Monday week-start dates of `fact_forecast_panel` rows where
`is_forecast_eligible = 1`. An origin week is eligible when **all four** conditions hold:

1. `week_index_in_cycle >= 4` (at least 4 weeks of history),
2. the week begins on or after `decision_window_start` of intake round 1,
3. the week begins on or before `enrolment_end_date`, and
4. `week_index_in_cycle + H <= total_weeks - 1` for **every** declared horizon `H`
   (currently `H ∈ {1, 2, 4, 6}`).

Condition 4 exists so that `origin + H` is always a **real, observed panel cell**. Without it
the last eligible week of a cycle would have a `+6 week` target that lies outside the cycle,
which would force the modeller to either drop those origins or invent a target. Making the
rule explicit in the generator means `is_forecast_eligible` is a guarantee, not a hint, and
`scripts/validate_dataset.py` can machine-check it (check family `TEMPORAL`,
`forecast_horizon_*_supported`).

Condition 2 restricts the enrolled-yield forecast to the post-decision window, which is the only
region where an enrolled-count forecast is informative. Outside that window the panel is still
fully present and remains valid for **verification-throughput** forecasting over
`cum_applications_verified` and `cum_applications_submitted`; the two tasks are documented
separately and must not be conflated.

---

## G. Core entities and relationships

| Entity | Grain (row = ) | Primary key | Foreign keys | Cardinality |
|---|---|---|---|---|
| `dim_funnel_stage` | one funnel stage | `stage_code` | — | 7 rows; referenced by every funnel event |
| `dim_admission_cycle` | one admission cycle | `cycle_id` | — | 4 rows |
| `dim_programme` | one programme | `programme_id` | `campus_region_id` → `dim_region` | 12 rows |
| `dim_region` | one applicant-origin region | `region_id` | — | 8 rows |
| `dim_campaign` | one marketing campaign | `campaign_id` | `cycle_id` → `dim_admission_cycle` | 2 intakes × 4 cycles × channels |
| `fact_applicant` | one applicant | `applicant_id` | `region_id` → `dim_region` | 1 : N → `fact_application` |
| `fact_application` | one application journey | `application_id` | `applicant_id`, `programme_id`, `cycle_id`, `campaign_id` | the ML unit |
| `fact_funnel_event` | one stage achievement | `event_id` | `application_id`, `programme_id`, `cycle_id`, `stage_code` | 1 : N (0–7) → `fact_application` |
| `fact_engagement` | one application × one activity date | `engagement_id` | `application_id`, `cycle_id` | 1 : N (0–14) → `fact_application` |
| `fact_forecast_panel` | programme × cycle × ISO week | `panel_id` | `programme_id`, `cycle_id` | 1 : N from programme and cycle |

### G.1 Relationship rules

- **R1** An applicant may hold 1..N applications; the same applicant may not hold two applications
  to the same programme in the same cycle.
- **R2** An applicant may apply in more than one cycle (re-application); this is allowed and is a
  natural source of cross-cycle cohort analysis.
- **R3** `fact_engagement` exists only for applications that reached `application_started`.
- **R4** `fact_funnel_event` is prefix-closed (invariant F1) and strictly chronological (F2).
- **R5** `campaign_id` is non-null only when `acquisition_channel ∈ {paid_search, social_media,
  email_campaign, partner_agency}`; it is null for `organic_search`, `referral`, `direct`,
  `education_fair`.
- **R6** Every `(programme_id, cycle_id)` pair appears in `fact_forecast_panel` for every week of
  the cycle window, whether or not it has activity.

### G.2 PII boundary

**The dataset contains no PII.** There are no names, emails, phone numbers, postal addresses, dates
of birth, government identifiers, or any other attribute that identifies a natural person.
`applicant_id` and `application_id` are synthetic surrogate keys with no external meaning. The only
quasi-identifying attributes are coarse and synthetic: `region_id` (8 regions), `gender_band`
(3 values), `education_level` (4 values). They are retained for segmentation and mix analysis and
must not be used as protected-attribute decision variables in this project.

---

## H. Data dictionary

Published separately at `docs/data_dictionary.md`. That file is **rendered directly from
`scripts/admitflow_schema.py`**, the single source of truth for the column registry, so
documentation and data cannot drift. Every field is classified as `GENERATED`, `DERIVED`, `TARGET`,
`POST_OUTCOME`, `KEY` or `REFERENCE`, and every field declares its availability at the prediction
point, its leakage risk, and its generation logic.

---

## I. Leakage boundaries

### I.1 SAFE prediction features (`primary` feature set)

Allowed at `application_submitted_ts`. Grouped by provenance:

- **Acquisition / attribution:** `acquisition_channel`, `acquisition_source`, `first_touch_date`,
  `touchpoints_count`, `is_multi_touch`, `is_referral_alumni`
- **Applicant:** `region_id`, `gender_band`, `education_level`, `is_repeat_applicant_at_prediction`
- **Programme / cycle context:** `programme_id`, `cycle_id`, `intake_round`, `annual_fee_inr`,
  `selectivity_tier`, `duration_years`, `review_duration_days`
- **Academic standing:** `academic_score_pct`, `academic_score_band`
- **Application quality at submission:** `doc_completeness_score`, `fee_scholarship_applied`
- **Application timing:** `inquiry_ts`, `application_started_ts`, `application_submitted_ts`,
  `days_inquiry_to_start`, `days_start_to_submit`, `days_inquiry_to_submit`,
  `days_to_round_close_at_start`, `week_of_cycle_at_submission`, `month_of_submission`
- **Engagement before submission:** `pre_sub_session_count`, `pre_sub_active_days`,
  `pre_sub_total_minutes`, `pre_sub_doc_uploads`, `pre_sub_form_fields_completed`,
  `pre_sub_return_visits`
- **Grouping / bookkeeping:** `cohort_label`, `split_hint`, `application_id`, `applicant_id`

### I.2 Additional features for the `decision` view

`application_verified_ts`, `doc_verification_status`, `doc_query_raised`, `doc_query_count`,
`days_submitted_to_verified`, plus everything in I.1.

### I.3 POST-OUTCOME fields — forbidden as features

| Field | Why it is a leak |
|---|---|
| `selection_score` | **The primary trap.** The institution's own merit score, computed at decision time from transcripts. It is the single strongest predictor of `admitted_flag` and does not exist at submission. |
| `decision_type` | The decision itself. |
| `admitted_flag` | A target (T-07), and an intermediate outcome. |
| `enrolled_flag`, `enrolled_given_admitted_flag` | The targets. |
| `stage_reached`, `stage_reached_order`, `dropoff_stage`, `dropoff_reason` | The entire downstream funnel, including the answer. |
| `application_verified_ts`, `admission_decision_ts`, `admitted_ts`, `enrolled_ts` | Future timestamps. |
| `doc_verification_status`, `doc_query_raised`, `doc_query_count` | Verification outcome, decided after submission. |
| `days_submitted_to_verified`, `days_verified_to_decision`, `days_decision_to_enrolled` | Future durations. |
| `offer_letter_issued`, `offer_deadline` | Issued after the decision. |
| `scholarship_offered`, `scholarship_amount_inr` | Awarded after the decision. |
| `withdrawn_flag`, `withdrawn_date` | Occurs after submission. |
| `fact_applicant.is_repeat_applicant` | A **lifetime** total across all cycles. Includes applications the applicant makes *after* the current prediction point, so it is not safe even though the concept sounds harmless. Use `fact_application.is_repeat_applicant_at_prediction` instead. |
| `fact_forecast_panel.cum_*` / `wk_*` at week `> T` | Post-origin panel values. The forecasting feature builder must slice, never look ahead. |

### I.4 Validation requirements for leakage

1. No column with role `POST_OUTCOME` or `TARGET` may appear in the `primary` or `decision` feature
   set. **Hard failure** if it does.
2. For every column in a feature set, the declared source timestamp column must satisfy
   `source_ts ≤ prediction_ts` on every row of the modelling view. **Hard failure** otherwise.
3. No column in a feature set may be a deterministic function of a target column. **Hard failure**
   if one exists.
4. No single feature may separate the target almost perfectly (rank AUC > 0.93). **Hard failure**
   — indicates the generator leaked the answer into a feature.
5. The raw table MUST retain `selection_score` (D-11) so that the leakage trap is real and the
   validator is meaningfully exercised.

---

## J. Attribution semantics

`fact_application` carries first-touch acquisition fields and assisted-touch counts. **These are
recorded associations, not causal effects.** Channel conversion differences arise because channels
attract different applicant mixes (region, education level, score distribution, programme intent),
not because the channel caused the difference. The dataset supports the *comparison*; it does not
support, and must not be used for, a causal claim. No uplift model, no causal inference, no
counterfactual estimate is licensed by this dataset.

---

## K. Synthetic generation assumptions

These are the **explicit** mechanisms used by the generator. They are assumptions about a fictional
system, not claims about any real one.

| # | Assumption |
|---|---|
| K-01 | A single fictional institution, not named, with 12 undergraduate programmes across faculties, running two intake rounds per cycle over four admission cycles (`AY2022-23` … `AY2025-26`). All four cycles are closed and finalised — the dataset contains **no open, partial or future cycle**, so every funnel outcome is observed. |
| K-02 | Programme demand differs by a fixed `demand_weight` and drifts year over year. |
| K-03 | **Demand crowding is endogenous.** When applications for a programme-cycle exceed a multiple of its seat capacity, the merit cutoff tightens and the admit rate falls. This is the mechanism that makes programme-level conversion analytically interesting. |
| K-04 | Programme selectivity is tiered (`emerging` / `medium` / `high`) and is a published attribute; the underlying merit cutoff is not. |
| K-05 | Each applicant carries unobserved latent factors: `z_ability` (academic), `z_intent` (motivation), `z_constraint` (financial/other). Only noisy projections of these are observable, which guarantees irreducible noise in the target. |
| K-06 | `academic_score_pct` is a noisy observation of `z_ability` (reporting noise), so score is informative but not sufficient. |
| K-07 | Engagement intensity is a latent quantity that influences both the start→submit transition and, independently, offer acceptance. Only its aggregate projection is observable. |
| K-08 | A partially unobserved `competing_offer` factor drives offer declines. Because it is never observed, no feature can predict acceptance precisely. This is the guarantee that the target is **not trivially predictable**. |
| K-09 | Every stage transition is a Bernoulli draw from a logistic model of observable + latent factors. There are **no deterministic rules and no thresholds** in the generator. |
| K-10 | Engagement is generated from a latent intensity first, then realised day by day, so that the *presence* of engagement cannot mechanically determine whether the application is submitted. |
| K-11 | Documentation queries are a sub-process inside verification: a query adds a delay and carries its own failure probability. |
| K-12 | Withdrawn applications never receive a decision. |
| K-13 | An offer lapses if acceptance would fall after the round's offer-accept deadline. |
| K-14 | All timestamps are timezone-naive, interpreted as local institutional time, stored in ISO-8601 (`YYYY-MM-DDTHH:MM:SS`). |
| K-15 | All IDs are synthetic, stable across runs for a fixed seed, and meaningless outside the dataset. |
| K-16 | `selectivity_tier`, `annual_fee_inr`, `review_duration_days` and `demand_weight` are published programme attributes and are therefore legitimate features; the latent merit cutoff is not published. |

---

## L. Known simplifications and limitations

| # | Limitation |
|---|---|
| L-01 | No waitlist state (D-02). |
| L-02 | Enrolment is a single milestone; registration and fee payment are not separable (T-03). |
| L-03 | Scholarship is an attribute of an offer, not a funnel (T-02). |
| L-04 | No programme-transfer, no lateral entry, no multiple-offer handling. |
| L-05 | Region granularity is coarse (T-01). |
| L-06 | `fact_engagement` is a daily aggregate, not a raw event log. Session-level modelling is out of scope. |
| L-07 | Attribution is first-touch plus an assist count, not a multi-touch attribution model. |
| L-08 | No financial-aid affordability data beyond `fee_scholarship_applied`; the `z_constraint` factor is unobserved by construction. |
| L-09 | Only one decision outcome type (`admit` / `reject`). |
| L-10 | The dataset is synthetic. Any performance measured on it measures the *generator's* assumptions, not any real institution. |
| L-11 | Cross-cycle re-application is emergent, not campaign-driven (T-04). |
| L-12 | The `primary` feature set is an allow-list; a new column added to the schema is **not** a feature until explicitly added to a feature set. |

---

## M. Reproducibility contract

1. `scripts/generate_dataset.py` is fully deterministic given `(seed, n_applications, n_cycles,
   start_cycle_year)`. Two runs with identical configuration produce byte-identical CSVs.
2. No wall-clock time, no hostname, no machine-specific path, and no unseeded randomness enters the
   data. The manifest records the configuration and a SHA-256 of every output file.
3. Randomness is drawn from independent `numpy.random.SeedSequence` children per generation stage,
   so changing one stage's size does not perturb the others.
4. Floating point columns are written with a fixed format (`%.6f`) to avoid repr-dependent churn.
5. Schema, dictionary, validator and profiler all read the same column registry
   (`scripts/admitflow_schema.py`), so a column cannot exist without being documented, classified
   and checked.
