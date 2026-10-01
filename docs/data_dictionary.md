# AdmitFlow — Data Dictionary

Rendered from `scripts/admitflow_schema.py`, the single source of truth for the column registry. Every column of every generated table is listed with its classification, prediction-time availability, leakage risk, feature-set membership and generation logic. If a column exists in the data but not in this file, the dataset is invalid.

> **SYNTHETIC DATA NOTICE**
>
> The primary project dataset is synthetic and was generated according to the documented AdmitFlow admission-funnel specification for development, experimentation, evaluation, and demonstration. It does not represent any real institution, applicant, or admission outcome.
>
> Any metric computed on this dataset is a property of the documented generator assumptions. It must never be reported as real-world institutional performance.


## How to read this dictionary

### Field classification

| Role | Meaning |
|---|---|
| `KEY` | Primary or foreign key. |
| `REFERENCE` | Published reference attribute of a dimension table. Not simulated output. |
| `GENERATED` | Drawn by the generator from the stated mechanism. |
| `DERIVED` | Computed deterministically from other columns of this dataset. |
| `TARGET` | A supervised prediction target. Forbidden as a feature. |
| `POST_OUTCOME` | Known only after the prediction point. FORBIDDEN as a feature of the primary target. |

### Prediction-time availability

| Value | Meaning |
|---|---|
| `pre_submission` | Content is fully determined strictly before `application_submitted_ts`. |
| `at_prediction_point` | Content is determined at or before `application_submitted_ts` and does not change afterwards. |
| `post_prediction_point` | Content is determined after `application_submitted_ts`. FORBIDDEN as a feature of the primary target. |
| `not_applicable` | Key, target, or reference attribute; not a predictive feature. |

### Leakage risk

| Value | Meaning |
|---|---|
| `none` | Safe. No content dated after the prediction point. |
| `low` | Safe but indirectly sensitive: a dimension attribute correlated with a protected attribute (region, gender) or with programme capacity. Usable; interpret with care. |
| `high` | Unsafe. Content is dated after the prediction point. Using it as a feature invalidates the evaluation. |

**`Source timestamp`** is the column that carries the moment at which the field's content became known. The validator checks against the *data* that this timestamp is not later than the prediction point for every column in a feature set. That check is what makes the leakage boundary machine-verified rather than merely documented.


### Nullability

Nullability is declared per column. A column may be `required` (it belongs to the entity and is always written) yet `nullable` (its value only exists for the subset of rows that reached a given funnel stage). See `STAGE_CONDITIONAL_COLUMNS` in `scripts/admitflow_schema.py` for the population of each such column.


| Field | Null when |
|---|---|
| `application_started_ts` | null unless the application reached `application_started` |
| `application_submitted_ts` | null unless the application reached `application_submitted` |
| `prediction_ts` | the prediction point; null unless the application was submitted |
| `prediction_stage` | the stage at the prediction point; null unless submitted |
| `academic_score_pct` | declared on the form at submission; null unless submitted |
| `academic_score_band` | banded from `academic_score_pct`; null unless submitted |
| `doc_completeness_score` | computed from the uploaded set at submission; null unless submitted |
| `days_inquiry_to_start` | null unless the application reached `application_started` |
| `days_start_to_submit` | null unless the application was submitted |
| `days_inquiry_to_submit` | null unless the application was submitted |
| `days_to_round_close_at_start` | null unless the application reached `application_started` |
| `week_of_cycle_at_submission` | null unless the application was submitted |
| `month_of_submission` | null unless the application was submitted |
| `pre_sub_session_count` | engagement summary; null unless the application was submitted |
| `pre_sub_active_days` | engagement summary; null unless the application was submitted |
| `pre_sub_total_minutes` | engagement summary; null unless the application was submitted |
| `pre_sub_doc_uploads` | engagement summary; null unless the application was submitted |
| `pre_sub_form_fields_completed` | engagement summary; null unless the application was submitted |
| `pre_sub_return_visits` | engagement summary; null unless the application was submitted |

### Feature sets

| Set | Population | Prediction point |
|---|---|---|
| `primary` | applications that reached `application_submitted` | `application_submitted_ts` |
| `decision` | applications that reached `admission_decision` | `admission_decision_ts` |

Feature sets are **allow-lists**. A column absent from a set is not a feature of that task.


## Entity index

| Table | Row grain | Primary key | Pipeline role |
|---|---|---|---|
| `dim_funnel_stage` | one row per admission funnel stage | `stage_code` | Funnel definition / analytics reference |
| `dim_region` | one row per applicant-origin region | `region_id` | Segmentation / cohort analysis dimension |
| `dim_programme` | one row per programme offered by the fictional institution | `programme_id` | Core analysis dimension for programme comparison and forecasting |
| `dim_admission_cycle` | one row per admission cycle | `cycle_id` | Time dimension, drives chronological splits and forecast origins |
| `dim_campaign` | one row per marketing campaign within an admission cycle | `campaign_id` | Attribution / funnel-attribution analysis |
| `fact_applicant` | one row per applicant | `applicant_id` | Entity resolution / cohort analysis; joined into the modelling view |
| `fact_application` | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | `application_id` | Primary ML unit; funnel analytics grain; source of the modelling view |
| `fact_funnel_event` | one row per application per achieved funnel stage (at most 7 rows per application) | `event_id` | Funnel analytics, conversion and drop-off analysis, forecast panel input |
| `fact_engagement` | one row per application per activity date, within the pre-submission window | `engagement_id` | Behavioural features; funnel progression explanation; explainability |
| `fact_forecast_panel` | one row per programme x admission cycle x ISO week (Monday start) | `panel_id` | Forecasting (T-F), yield-curve analytics, scenario simulation |

---

## `dim_funnel_stage`

**Row grain.** one row per admission funnel stage


**Primary key.** `stage_code`


**Purpose.** Reference ladder of the seven AdmitFlow admission funnel stages, including re-entry and ordering semantics used by validation.


**Column count.** 7


| Field | Type | Role | Row grain | Required | Availability at prediction point | Source timestamp | Leakage risk | In feature set | Description | Generation logic | Example / allowed values |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `stage_order` | `int64` | REFERENCE | one row per admission funnel stage | yes | not_applicable | `` | none | — | Integer position of the stage in the ladder (1..7). | Fixed constant ladder declared in the analytical contract. | 1 |
| `stage_code` | `str` | KEY | one row per admission funnel stage | yes | not_applicable | `` | none | — | Stable machine key of the stage. | Fixed constant declared in the analytical contract. | application_submitted<br>`prospect`, `application_started`, `application_submitted`, `application_verified`, `admission_decision`, `admitted`, `enrolled` |
| `stage_name` | `str` | REFERENCE | one row per admission funnel stage | yes | not_applicable | `` | none | — | Human readable stage name. | Fixed constant. | Application submitted |
| `stage_kind` | `str` | REFERENCE | one row per admission funnel stage | yes | not_applicable | `` | none | — | Whether the stage is a cumulative milestone or a discrete event. | Fixed constant; all AdmitFlow stages are cumulative milestones. | CUMULATIVE_MILESTONE<br>`CUMULATIVE_MILESTONE`, `EVENT` |
| `allows_reentry` | `bool` | REFERENCE | one row per admission funnel stage | yes | not_applicable | `` | none | — | Whether the stage can be re-entered after being left. | Fixed constant. Session-level revisits of `application_started` are recorded as engagement days, not as repeated milestones. | False |
| `requires_all_prior_stages` | `bool` | REFERENCE | one row per admission funnel stage | yes | not_applicable | `` | none | — | Whether reaching the stage requires every earlier stage to have been reached. | Fixed constant, True for all stages (prefix-closed funnel, invariant F1). | True |
| `stage_description` | `str` | REFERENCE | one row per admission funnel stage | yes | not_applicable | `` | none | — | Full definition, entry condition and exit condition of the stage. | Fixed constant transcribed from the analytical contract. | Application payload submitted on or before the intake round close date. |

---

## `dim_region`

**Row grain.** one row per applicant-origin region


**Primary key.** `region_id`


**Purpose.** Fictional coarse geography of applicant origin. Deliberately coarse: the dataset carries no PII and no sub-district detail.


**Column count.** 5


| Field | Type | Role | Row grain | Required | Availability at prediction point | Source timestamp | Leakage risk | In feature set | Description | Generation logic | Example / allowed values |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `region_id` | `str` | KEY | one row per applicant-origin region | yes | not_applicable | `` | none | — | Region key. | Fixed constant dimension. | REG-04 |
| `region_name` | `str` | REFERENCE | one row per applicant-origin region | yes | not_applicable | `` | none | — | Fictional region name. | Fixed constant dimension. | Coastal South |
| `region_type` | `str` | REFERENCE | one row per applicant-origin region | yes | not_applicable | `` | low | — | Settlement type of the region. | Fixed constant dimension. | tier2<br>`metro`, `tier2`, `tier3`, `rural_remote` |
| `mean_distance_km_to_campus` | `float64` | GENERATED | one row per applicant-origin region | yes | pre_submission | `inquiry_ts` | low | `primary`, `decision` | Mean travel distance from the region to the institution campus; a proxy for relocation cost and therefore for offer acceptance. | Fixed constant per region, then perturbed +/-12% per cycle to create mild year-over-year variation. | 842.5 |
| `region_inquiry_weight` | `float64` | GENERATED | one row per applicant-origin region | yes | pre_submission | `inquiry_ts` | low | `primary`, `decision` | Share of prospects originating in the region. | Fixed constant share weights, renormalised across regions; drifts +/-10% per cycle. | 0.145 |

---

## `dim_programme`

**Row grain.** one row per programme offered by the fictional institution


**Primary key.** `programme_id`


**Purpose.** Programme reference data. Contains only PUBLISHED programme attributes; the latent merit cutoff that actually drives decisions is deliberately withheld.


**Column count.** 12


| Field | Type | Role | Row grain | Required | Availability at prediction point | Source timestamp | Leakage risk | In feature set | Description | Generation logic | Example / allowed values |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `programme_id` | `str` | KEY | one row per programme offered by the fictional institution | yes | not_applicable | `` | none | — | Programme key. | Fixed constant dimension. | PGM-07 |
| `programme_name` | `str` | REFERENCE | one row per programme offered by the fictional institution | yes | not_applicable | `` | none | — | Programme name. | Fixed constant dimension. | B.Sc. Computer Science |
| `programme_code` | `str` | REFERENCE | one row per programme offered by the fictional institution | yes | not_applicable | `` | none | — | Short programme code. | Fixed constant dimension. | BSC-CS |
| `faculty` | `str` | REFERENCE | one row per programme offered by the fictional institution | yes | not_applicable | `` | none | — | Faculty the programme belongs to. | Fixed constant dimension. | Faculty of Science<br>`Faculty of Science`, `Faculty of Commerce`, `Faculty of Management`, `Faculty of Humanities`, `Faculty of Technology` |
| `award_level` | `str` | REFERENCE | one row per programme offered by the fictional institution | yes | not_applicable | `` | none | — | Award level of the programme. | Fixed constant dimension, all undergraduate. | UG<br>`UG` |
| `duration_years` | `int64` | GENERATED | one row per programme offered by the fictional institution | yes | pre_submission | `inquiry_ts` | low | `primary`, `decision` | Programme duration in years. | Fixed constant per programme. | 3 |
| `annual_fee_inr` | `int64` | GENERATED | one row per programme offered by the fictional institution | yes | pre_submission | `inquiry_ts` | low | `primary`, `decision` | Published annual tuition fee in INR; a driver of offer acceptance through the unobserved financial-constraint factor. | Log-normal draw per programme, rounded to the nearest 500 INR. | 146000 |
| `base_seat_capacity` | `int64` | GENERATED | one row per programme offered by the fictional institution | yes | pre_submission | `inquiry_ts` | low | `primary`, `decision` | Approved intake capacity for one admission cycle. | Fixed constant per programme. | 120 |
| `selectivity_tier` | `str` | REFERENCE | one row per programme offered by the fictional institution | yes | pre_submission | `inquiry_ts` | low | `primary`, `decision` | Published selectivity band. | Fixed constant per programme. | high<br>`emerging`, `medium`, `high` |
| `review_duration_days` | `float64` | GENERATED | one row per programme offered by the fictional institution | yes | pre_submission | `inquiry_ts` | low | `primary`, `decision` | Median days from submission to document verification. | Fixed constant per programme, derived from faculty workload. | 6.4 |
| `demand_weight` | `float64` | GENERATED | one row per programme offered by the fictional institution | yes | pre_submission | `inquiry_ts` | low | `primary`, `decision` | Relative attractiveness driving how many prospects the programme attracts. | Fixed constant per programme, renormalised across programmes; drifts year over year. | 0.131 |
| `campus_region_id` | `str` | KEY | one row per programme offered by the fictional institution | yes | pre_submission | `inquiry_ts` | low | `primary`, `decision` | Region in which the programme is taught. | Fixed constant dimension. | REG-01 |

---

## `dim_admission_cycle`

**Row grain.** one row per admission cycle


**Primary key.** `cycle_id`


**Purpose.** Calendar and deadline structure of an admission cycle, including both intake rounds. All four cycles in this dataset are closed and fully finalised.


**Column count.** 20


| Field | Type | Role | Row grain | Required | Availability at prediction point | Source timestamp | Leakage risk | In feature set | Description | Generation logic | Example / allowed values |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `cycle_id` | `str` | KEY | one row per admission cycle | yes | not_applicable | `` | none | — | Admission cycle key. | Fixed constant dimension. | CYC-2024 |
| `academic_year_label` | `str` | REFERENCE | one row per admission cycle | yes | not_applicable | `` | none | — | Human readable academic year. | Derived from the cycle start year. | AY2024-25 |
| `cycle_start_date` | `date` | DERIVED | one row per admission cycle | yes | not_applicable | `` | none | — | First day of the cycle (equal to intake 1 application open date). | Derived: intake 1 application open date. | 2024-06-01 |
| `cycle_end_date` | `date` | DERIVED | one row per admission cycle | yes | not_applicable | `` | none | — | Last day of the cycle (equal to intake 2 enrolment end date). | Derived: intake 2 enrolment end date. | 2025-03-20 |
| `intake1_application_open` | `date` | REFERENCE | one row per admission cycle | yes | not_applicable | `` | none | — | Intake 1 applications open. | Fixed cycle template. | 2024-06-01 |
| `intake1_application_close` | `date` | REFERENCE | one row per admission cycle | yes | not_applicable | `` | none | — | Intake 1 application submission deadline. Determines `intake_round` at prospect time. | Fixed cycle template. | 2024-10-15 |
| `intake1_decision_start` | `date` | REFERENCE | one row per admission cycle | yes | not_applicable | `` | none | — | First day of the intake 1 decision release window. | Fixed cycle template. | 2024-11-20 |
| `intake1_decision_end` | `date` | REFERENCE | one row per admission cycle | yes | not_applicable | `` | none | — | Last day of the intake 1 decision release window. | Fixed cycle template. | 2024-11-27 |
| `intake1_offer_deadline` | `date` | REFERENCE | one row per admission cycle | yes | not_applicable | `` | none | — | Last date on which an intake 1 offer can be accepted. | Fixed cycle template. | 2025-01-10 |
| `intake1_enrolment_end` | `date` | REFERENCE | one row per admission cycle | yes | not_applicable | `` | none | — | Last date of intake 1 registration and fee payment. | Fixed cycle template. | 2025-02-05 |
| `intake2_application_open` | `date` | REFERENCE | one row per admission cycle | yes | not_applicable | `` | none | — | Intake 2 applications open (day after intake 1 close). | Fixed cycle template. | 2024-10-16 |
| `intake2_application_close` | `date` | REFERENCE | one row per admission cycle | yes | not_applicable | `` | none | — | Intake 2 application submission deadline. | Fixed cycle template. | 2024-12-20 |
| `intake2_decision_start` | `date` | REFERENCE | one row per admission cycle | yes | not_applicable | `` | none | — | First day of the intake 2 decision release window. | Fixed cycle template. | 2025-01-15 |
| `intake2_decision_end` | `date` | REFERENCE | one row per admission cycle | yes | not_applicable | `` | none | — | Last day of the intake 2 decision release window. | Fixed cycle template. | 2025-01-22 |
| `intake2_offer_deadline` | `date` | REFERENCE | one row per admission cycle | yes | not_applicable | `` | none | — | Last date on which an intake 2 offer can be accepted. | Fixed cycle template. | 2025-02-25 |
| `intake2_enrolment_end` | `date` | REFERENCE | one row per admission cycle | yes | not_applicable | `` | none | — | Last date of intake 2 registration and fee payment. | Fixed cycle template. | 2025-03-20 |
| `verification_end_date` | `date` | DERIVED | one row per admission cycle | yes | not_applicable | `` | none | — | Last day on which document verification may be completed. | Derived: intake 2 application close + 4 days. | 2024-12-24 |
| `total_weeks` | `int64` | DERIVED | one row per admission cycle | yes | not_applicable | `` | none | — | Number of ISO weeks spanned by the cycle; the panel row count per programme-cycle. | Derived: ISO weeks between cycle_start_date and cycle_end_date inclusive. | 43 |
| `is_finalised` | `bool` | REFERENCE | one row per admission cycle | yes | not_applicable | `` | none | — | True once all outcomes of the cycle are known. All cycles shipped here are finalised, so no funnel outcome is censored. | Fixed constant, True for every cycle in this dataset. | True |
| `total_seats_offers` | `int64` | DERIVED | one row per admission cycle | yes | not_applicable | `` | none | — | Sum of seat capacity across all programmes in the cycle. | Derived: sum of `dim_programme.base_seat_capacity`. | 1180 |

---

## `dim_campaign`

**Row grain.** one row per marketing campaign within an admission cycle


**Primary key.** `campaign_id`


**Purpose.** Fictional paid / owned marketing campaigns. Only channels that can be attributed to a campaign reference this table; organic, referral, direct and education-fair leads have a null `campaign_id`.


**Column count.** 9


| Field | Type | Role | Row grain | Required | Availability at prediction point | Source timestamp | Leakage risk | In feature set | Description | Generation logic | Example / allowed values |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `campaign_id` | `str` | KEY | one row per marketing campaign within an admission cycle | yes | not_applicable | `` | none | — | Campaign key. | Fixed constant dimension. | CMP-2024-PAID-01 |
| `campaign_name` | `str` | REFERENCE | one row per marketing campaign within an admission cycle | yes | not_applicable | `` | none | — | Campaign name. | Fixed constant dimension. | AY2024 Prospecting - Search Brand |
| `channel` | `str` | REFERENCE | one row per marketing campaign within an admission cycle | yes | not_applicable | `` | none | — | Channel the campaign runs on. | Fixed constant dimension. | paid_search<br>`organic_search`, `paid_search`, `social_media`, `email_campaign`, `referral`, `direct`, `education_fair`, `partner_agency` |
| `cycle_id` | `str` | KEY | one row per marketing campaign within an admission cycle | yes | not_applicable | `` | none | — | Admission cycle the campaign belongs to. | Fixed constant dimension. | CYC-2024 |
| `start_date` | `date` | REFERENCE | one row per marketing campaign within an admission cycle | yes | pre_submission | `first_touch_date` | none | — | Campaign start date. | Fixed constant, inside the cycle application window. | 2024-06-01 |
| `end_date` | `date` | REFERENCE | one row per marketing campaign within an admission cycle | yes | pre_submission | `first_touch_date` | none | — | Campaign end date. | Fixed constant, inside the cycle application window. | 2024-12-20 |
| `planned_budget_inr` | `int64` | GENERATED | one row per marketing campaign within an admission cycle | yes | pre_submission | `first_touch_date` | none | — | Planned campaign budget in INR. | Log-normal draw per campaign, rounded to the nearest 5000 INR. | 850000 |
| `target_group` | `str` | REFERENCE | one row per marketing campaign within an admission cycle | yes | not_applicable | `` | none | — | Intended audience segment, recorded for slice-based attribution analysis. | Fixed constant dimension. | science_and_technology<br>`science_and_technology`, `commerce_and_management`, `all_programmes`, `open_house_followup` |
| `is_active` | `bool` | REFERENCE | one row per marketing campaign within an admission cycle | yes | not_applicable | `` | none | — | Whether the campaign ran to plan. | Fixed constant, True for all campaigns here. | True |

---

## `fact_applicant`

**Row grain.** one row per applicant


**Primary key.** `applicant_id`


**Purpose.** Applicant master. Contains NO PII: no name, email, phone, address, date of birth or government identifier. `applicant_id` is a synthetic surrogate key.


**Column count.** 7


| Field | Type | Role | Row grain | Required | Availability at prediction point | Source timestamp | Leakage risk | In feature set | Description | Generation logic | Example / allowed values |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `applicant_id` | `str` | KEY | one row per applicant | yes | not_applicable | `` | none | — | Synthetic applicant surrogate key. Carries no external meaning. | Sequential synthetic key allocated at applicant creation. | APL-0041821 |
| `region_id` | `str` | KEY | one row per applicant | yes | pre_submission | `inquiry_ts` | low | `primary`, `decision` | Applicant origin region. | Sampled from `dim_region` enquiry shares at first inquiry, then frozen for the applicant's lifetime. | REG-04 |
| `gender_band` | `str` | GENERATED | one row per applicant | yes | pre_submission | `inquiry_ts` | low | `primary`, `decision` | Self-reported gender band, synthetic. Used for programme mix and segmentation only, never as a decision variable. | Categorical draw from regional base rates with a mild programme-specific mix shift applied on programme choice. | female<br>`female`, `male`, `other_or_prefer_not_to_say` |
| `education_level` | `str` | GENERATED | one row per applicant | yes | pre_submission | `inquiry_ts` | low | `primary`, `decision` | Highest qualification held at the time of the first application. | Categorical draw, with diploma and undergraduate candidates concentrated in management and commerce programmes. | higher_secondary<br>`higher_secondary`, `diploma`, `undergraduate`, `other` |
| `first_inquiry_date` | `date` | DERIVED | one row per applicant | yes | pre_submission | `inquiry_ts` | low | — | Date of the applicant's first ever inquiry. | Derived: min(inquiry_ts) over the applicant's applications. | 2023-07-14 |
| `application_count` | `int64` | DERIVED | one row per applicant | yes | pre_submission | `inquiry_ts` | low | `primary`, `decision` | Number of applications held by this applicant across all cycles. | Derived: count of fact_application rows per applicant_id. | 2 |
| `is_repeat_applicant` | `bool` | DERIVED | one row per applicant | yes | post_prediction_point | `` | high | — | True if the applicant holds more than one application across their WHOLE history, including applications made after the current prediction point. Therefore NOT a safe feature - use `fact_application.is_repeat_applicant_at_prediction` instead. | Derived: application_count > 1 over all cycles. | True |

---

## `fact_application`

**Row grain.** one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage


**Primary key.** `application_id`


**Purpose.** The central fact table and the unit of record for the whole project. Carries pre-submission features, the explicit prediction point, the post-submission funnel outcome and the targets.


**Column count.** 61


| Field | Type | Role | Row grain | Required | Availability at prediction point | Source timestamp | Leakage risk | In feature set | Description | Generation logic | Example / allowed values |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `application_id` | `str` | KEY | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | not_applicable | `` | none | — | Synthetic application surrogate key. One row = one applicant's journey to one programme in one cycle, opened at the prospect stage. | Sequential synthetic key. | APP-0128447 |
| `applicant_id` | `str` | KEY | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | not_applicable | `` | none | — | Owning applicant. | FK to fact_applicant. | APL-0041821 |
| `programme_id` | `str` | KEY | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | pre_submission | `inquiry_ts` | low | `primary`, `decision` | Programme applied to. | FK to dim_programme; sampled proportional to programme demand weight. | PGM-07 |
| `cycle_id` | `str` | KEY | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | pre_submission | `inquiry_ts` | low | `primary`, `decision` | Admission cycle. | FK to dim_admission_cycle. | CYC-2024 |
| `campaign_id` | `str` | KEY | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | pre_submission | `first_touch_date` | low | `primary`, `decision` | Attributed campaign. Null unless the acquisition channel is campaign-bearing. | Sampled from campaigns of the same channel and cycle whose active window contains the first touch; null for organic_search, referral, direct and education_fair. | CMP-2024-PAID-01 |
| `acquisition_channel` | `str` | GENERATED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | pre_submission | `first_touch_date` | low | `primary`, `decision` | First-touch acquisition channel. ASSOCIATION ONLY: differences across channels reflect different applicant mixes and must not be read as causal lift. | Categorical draw from channel mix weights that drift by cycle and intake round. | organic_search<br>`organic_search`, `paid_search`, `social_media`, `email_campaign`, `referral`, `direct`, `education_fair`, `partner_agency` |
| `acquisition_source` | `str` | GENERATED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | pre_submission | `first_touch_date` | low | `primary`, `decision` | Specific source / sub-channel within `acquisition_channel`. | Uniform draw within the chosen channel's source list. | google_organic<br>`google_organic`, `bing_organic`, `programme_page`, `content_blog`, `google_ads_brand`, `google_ads_generic`, `meta_ads_prospect`, `instagram_organic`, `linkedin_organic`, `youtube_organic`, `meta_ads_retarget`, `newsletter_prospectus`, `alumni_referral_mail`, `open_day_invite`, `alumni_referral`, `parent_referral`, `school_counsellor`, `peer_referral`, `direct_web`, `app_download`, `walk_in`, `school_fair`, `district_career_fair`, `college_career_fair`, … (+3 more) |
| `first_touch_date` | `str` | GENERATED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | pre_submission | `first_touch_date` | low | `primary`, `decision` | Date of the applicant's first recorded marketing touch. Always on or before `inquiry_ts`. | inquiry_date minus a Gamma-distributed lead lag; clipped to the cycle application window. | 2024-06-14 |
| `touchpoints_count` | `int64` | GENERATED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | pre_submission | `first_touch_date` | low | `primary`, `decision` | Number of recorded marketing touchpoints before the inquiry. | 1 + Poisson(mean 2.2) with a channel-dependent rate; capped at 12. | 4 |
| `is_multi_touch` | `bool` | GENERATED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | pre_submission | `first_touch_date` | low | `primary`, `decision` | True if the prospect had more than one touchpoint before inquiring. | Derived: touchpoints_count > 1. | True |
| `is_referral_alumni` | `bool` | GENERATED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | pre_submission | `first_touch_date` | low | `primary`, `decision` | True if the referral came from an alumnus. | Bernoulli(0.28) when acquisition_channel == 'referral', else False. | False |
| `intake_round` | `int64` | GENERATED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | pre_submission | `inquiry_ts` | low | `primary`, `decision` | Intake round this application belongs to, fixed at prospect creation from the inquiry date relative to the intake 1 close date. Governs the submission deadline, decision window and offer deadline that apply. | 1 if inquiry_date <= intake1_application_close else 2. | 1 |
| `academic_score_pct` | `float64` | GENERATED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | at_prediction_point | `application_submitted_ts` | low | `primary`, `decision` | Percentage score on the qualifying examination, as reported at submission. A noisy observation of the latent ability factor (correlation approx. 0.8), so it is strongly but not perfectly informative. | N(58 + 9 * z_ability + 5 * reporting_noise, 4) clipped to [40, 99], rounded to 1 dp. | 78.0 |
| `academic_score_band` | `str` | DERIVED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | at_prediction_point | `application_submitted_ts` | low | `primary`, `decision` | Banded academic score. Derived ONLY from `academic_score_pct`, which is known at submission; it is not the post-decision merit score. | Derived: banding of academic_score_pct. | 70_79<br>`lt_60`, `60_69`, `70_79`, `80_89`, `90_plus` |
| `doc_completeness_score` | `float64` | GENERATED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | at_prediction_point | `application_submitted_ts` | low | `primary`, `decision` | Completeness of the supporting document set as assessed at submission, in [0.15, 1.0]. Drives the probability that verification succeeds. | clip(sigmoid(1.35 + 1.1 * z_ability + 0.8 * z_intent - 0.9 * log1p(1/days_available)) + N(0, 0.08), 0.15, 1.0), rounded to 4 dp. | 0.8421 |
| `fee_scholarship_applied` | `bool` | GENERATED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | at_prediction_point | `application_submitted_ts` | low | `primary`, `decision` | True if the applicant applied for fee concession or scholarship at submission. A weak observable proxy for financial constraint; the dominant factor remains unobserved. | Bernoulli depending on education level, region type and the latent financial-constraint factor. | False |
| `is_repeat_applicant_at_prediction` | `bool` | DERIVED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | at_prediction_point | `application_submitted_ts` | low | `primary`, `decision` | True if, at the moment this application was submitted, the applicant already held at least one other SUBMITTED application. This is the leakage-safe version of the lifetime `fact_applicant.is_repeat_applicant` flag, which must never be used as a feature. | Derived in a post-pass: count distinct applicant_ids over applications with application_submitted_ts <= this application's submission timestamp, then compare > 1. | False |
| `inquiry_ts` | `str` | GENERATED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | pre_submission | `inquiry_ts` | none | `primary`, `decision` | Timestamp of the inquiry that opened this application. Equals the `prospect` funnel event timestamp. | Beta-shaped draw over the intake round inquiry window, plus an intraday hour offset. | 2024-07-03T10:42:00 |
| `application_started_ts` | `str` | GENERATED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | pre_submission | `application_started_ts` | none | `primary`, `decision` | Timestamp of the first form session. Equals the `application_started` funnel event timestamp. Strictly after inquiry_ts and never after the round close date. | inquiry_ts + Gamma(1.4, 2.2) days, clipped to the round close date. | 2024-07-06T18:05:00 |
| `application_submitted_ts` | `str` | DERIVED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | at_prediction_point | `application_submitted_ts` | none | `primary`, `decision` | Timestamp of submission. Equals the `application_submitted` funnel event timestamp and IS the prediction point of the primary task. | application_started_ts + Gamma(1.8, 1.9) days, clipped to the round close date; always >= 1 day after application_started_ts. | 2024-07-11T20:14:00 |
| `prediction_ts` | `str` | DERIVED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | at_prediction_point | `` | none | — | Explicit prediction timestamp for the primary task. Equal to `application_submitted_ts`; declared separately so that the leakage boundary is machine readable. | Derived: alias of application_submitted_ts. | 2024-07-11T20:14:00 |
| `prediction_stage` | `str` | DERIVED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | at_prediction_point | `` | none | — | Funnel stage at which the primary prediction is made. | Fixed constant. | application_submitted<br>`application_submitted` |
| `days_inquiry_to_start` | `int64` | DERIVED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | pre_submission | `application_started_ts` | none | `primary`, `decision` | Days from inquiry to first form session. | Derived: floor of the timestamp difference. | 3 |
| `days_start_to_submit` | `int64` | DERIVED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | at_prediction_point | `application_submitted_ts` | none | `primary`, `decision` | Days from first form session to submission. | Derived: floor of the timestamp difference. | 5 |
| `days_inquiry_to_submit` | `int64` | DERIVED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | at_prediction_point | `application_submitted_ts` | none | `primary`, `decision` | Days from inquiry to submission. The single strongest behavioural summary of intent. | Derived: floor of the timestamp difference. | 8 |
| `days_to_round_close_at_start` | `int64` | DERIVED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | pre_submission | `application_started_ts` | none | `primary`, `decision` | Days remaining from the first form session to the intake round close date. Captures deadline pressure; small values strongly reduce submission probability. | Derived: (round close date - date(application_started_ts)) in days. | 101 |
| `week_of_cycle_at_submission` | `int64` | DERIVED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | at_prediction_point | `application_submitted_ts` | none | `primary`, `decision` | ISO week index of the submission week relative to the cycle start week (0-based). | Derived from submission date and cycle_start_date. | 7 |
| `month_of_submission` | `int64` | DERIVED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | at_prediction_point | `application_submitted_ts` | none | `primary`, `decision` | Calendar month of submission (1-12). | Derived from application_submitted_ts. | 7 |
| `pre_sub_session_count` | `int64` | DERIVED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | pre_submission | `application_submitted_ts` | none | `primary`, `decision` | Total pre-submission sessions in `fact_engagement`. | Derived: sum of session_count over engagement rows with activity_date <= date(prediction_ts). | 9 |
| `pre_sub_active_days` | `int64` | DERIVED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | pre_submission | `application_submitted_ts` | none | `primary`, `decision` | Number of distinct pre-submission activity dates. | Derived: count of engagement rows with activity_date <= date(prediction_ts). | 6 |
| `pre_sub_total_minutes` | `float64` | DERIVED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | pre_submission | `application_submitted_ts` | none | `primary`, `decision` | Total minutes of pre-submission portal activity. | Derived: sum of total_minutes over engagement rows up to the prediction date. | 212.5 |
| `pre_sub_doc_uploads` | `int64` | DERIVED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | pre_submission | `application_submitted_ts` | none | `primary`, `decision` | Documents uploaded before submission. | Derived: sum of docs_uploaded. | 4 |
| `pre_sub_form_fields_completed` | `int64` | DERIVED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | pre_submission | `application_submitted_ts` | none | `primary`, `decision` | Form fields completed before submission. | Derived: sum of form_fields_completed. | 57 |
| `pre_sub_return_visits` | `int64` | DERIVED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | pre_submission | `application_submitted_ts` | none | `primary`, `decision` | Pre-submission sessions that were return visits (not the applicant's first session). | Derived: sum of is_return_visit. | 5 |
| `stage_reached` | `str` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | post_prediction_point | `` | high | — | Highest funnel stage reached by this application. CONTAINS THE ANSWER - never a feature. | Derived: max stage_order present in fact_funnel_event for this application. | admitted<br>`prospect`, `application_started`, `application_submitted`, `application_verified`, `admission_decision`, `admitted`, `enrolled` |
| `stage_reached_order` | `int64` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | post_prediction_point | `` | high | — | Integer position of `stage_reached`. CONTAINS THE ANSWER - never a feature. | Derived from fact_funnel_event. | 6 |
| `dropoff_stage` | `str` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | post_prediction_point | `` | high | — | Stage at which the application left the funnel. Null when enrolled. | Derived: equal to stage_reached when stage_reached != 'enrolled'. | admitted<br>`prospect`, `application_started`, `application_submitted`, `application_verified`, `admission_decision`, `admitted`, `enrolled` |
| `dropoff_reason` | `str` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | post_prediction_point | `` | high | — | Single categorical reason for leaving the funnel. Null when enrolled. | Categorical draw from the reason list valid for the stage where the transition failed. | offer_not_accepted<br>`no_response`, `browsed_only`, `enquiry_closed_unqualified`, `form_abandoned`, `deadline_missed`, `requirements_unclear`, `incomplete_documents`, `ineligible_qualification`, `verification_timeout`, `withdrawn_by_applicant`, `accepted_elsewhere_withdrawn`, `below_merit_cutoff`, `eligibility_criteria_failed`, `capacity_exhausted`, `offer_not_accepted`, `chose_other_institution`, `financial_constraint`, `offer_deadline_lapsed` |
| `doc_query_raised` | `bool` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | post_prediction_point | `` | high | — | True if document clarification was requested during verification. | Bernoulli from a logistic model of `doc_completeness_score`, education level and channel. | True |
| `doc_query_count` | `int64` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | post_prediction_point | `` | high | — | Number of document clarification requests raised. | 0, or 1 + Poisson(0.4) when a query was raised. | 1 |
| `doc_verification_status` | `str` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | post_prediction_point | `` | high | — | Verification outcome for the application. | Derived from the doc-query sub-process: verified / returned_for_correction / rejected_ineligible / not_initiated. | verified<br>`verified`, `returned_for_correction`, `rejected_ineligible`, `not_initiated` |
| `application_verified_ts` | `str` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | post_prediction_point | `` | high | — | Timestamp at which verification was granted. Strictly after submission. | submission + programme review duration * lognormal noise + any doc-query delay. | 2024-07-20T15:31:00 |
| `admission_decision_ts` | `str` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | post_prediction_point | `` | high | — | Timestamp at which the decision was released. | Intake decision window start + programme offset (0-10 days) + jitter (0-2 days), pushed later if verification finished after the window opened. | 2024-11-22T11:00:00 |
| `admitted_ts` | `str` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | post_prediction_point | `` | high | — | Timestamp at which the offer was dispatched and the seat confirmed. Strictly after `admission_decision_ts` (contract invariant F2). | decision_ts + Uniform(3, 60) hours - the offer is issued by admissions after the committee decision is released. | 2024-11-23T14:20:00 |
| `enrolled_ts` | `str` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | post_prediction_point | `` | high | — | Timestamp at which registration and first fee instalment were completed. THE ANSWER. | admitted_ts + Gamma(2.2, 5.5) days, truncated at the round offer deadline; null when the offer was not accepted in time. | 2024-12-18T09:12:00 |
| `days_submitted_to_verified` | `int64` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | post_prediction_point | `` | high | — | Days from submission to verification. | Derived: floor of the timestamp difference. | 9 |
| `days_verified_to_decision` | `int64` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | post_prediction_point | `` | high | — | Days from verification to decision release. | Derived: floor of the timestamp difference. | 64 |
| `days_decision_to_enrolled` | `int64` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | post_prediction_point | `` | high | — | Days from decision to enrolment for admitted applicants. | Derived: floor of the timestamp difference. | 26 |
| `decision_type` | `str` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | post_prediction_point | `` | high | — | Formal decision released. THE DECISION ITSELF - never a feature. | Bernoulli from the programme/cycle merit model, or 'reject' if verification failed or the applicant withdrew. | admit<br>`admit`, `reject` |
| `selection_score` | `float64` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | post_prediction_point | `` | high | — | The institution's internal merit score, computed at decision time from transcripts, eligibility and category. THIS IS THE DELIBERATE LEAKAGE TRAP: it is the single strongest predictor of the decision and does not exist at submission. Retained in the raw table on purpose; the validator fails if it enters a feature set. | Derived from academic_score_pct, education level, programme quota mix and the latent ability factor; only defined for applications that reached a decision. | 78.42 |
| `offer_letter_issued` | `bool` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | post_prediction_point | `` | high | — | True if an offer letter was issued. | Derived: decision_type == 'admit'. | True |
| `offer_deadline` | `str` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | post_prediction_point | `` | high | — | Last date the offer could be accepted. | Round offer deadline + programme jitter of 0-4 days. | 2025-01-10 |
| `scholarship_offered` | `bool` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | post_prediction_point | `` | high | — | True if a fee concession accompanied the offer. | Bernoulli from merit margin and programme scholarship budget. | False |
| `scholarship_amount_inr` | `int64` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | post_prediction_point | `` | high | — | Annual concession amount in INR. Zero when no scholarship was offered. | 0 when not offered, else a draw scaled by merit margin and fee. | 0 |
| `withdrawn_flag` | `bool` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | post_prediction_point | `` | high | — | True if the applicant withdrew after submission. | Bernoulli(0.018) between verification and the decision window. | False |
| `withdrawn_date` | `str` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | post_prediction_point | `` | high | — | Date of withdrawal. Null when the applicant did not withdraw. | verified_ts + Uniform(1, 20) days when withdrawn. | — |
| `admitted_flag` | `int64` | POST_OUTCOME | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | post_prediction_point | `` | high | — | 1 if the applicant was admitted. STRUCTURALLY FORBIDDEN as a feature: it is an intermediate outcome of the primary target and a legitimate secondary target for an admission-offer model. | Derived: stage_reached_order >= 6. | 1 |
| `enrolled_given_admitted_flag` | `int64` | TARGET | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | no (nullable) | post_prediction_point | `` | high | — | Conditional target: 1 if an ADMITTED applicant went on to enrol. Null for applications that never reached `admitted`. Predicted at `admission_decision_ts` using the `decision` feature set. | Derived: 1 if stage_reached_order == 7, else 0 for admitted, null otherwise. | 1 |
| `enrolled_flag` | `int64` | TARGET | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | post_prediction_point | `` | high | — | PRIMARY TARGET. 1 if the applicant completed registration for this programme in this cycle. Predicted at `application_submitted_ts` using the `primary` feature set. | Derived: 1 if stage_reached_order == 7 else 0. | 1 |
| `cohort_label` | `str` | DERIVED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | pre_submission | `inquiry_ts` | low | `primary`, `decision` | Programme x cycle cohort key used for cohort analysis and dashboards. | Derived: programme_code + '-' + cycle_id. | BSC-CS-CYC-2024 |
| `split_hint` | `str` | DERIVED | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | yes | pre_submission | `inquiry_ts` | low | `primary`, `decision` | Chronological split hint derived ONLY from `cycle_id` (earliest cycles train, latest test). Never a function of the target. | Deterministic mapping of sorted cycle_id to train / validation / test. | train<br>`train`, `validation`, `test` |

---

## `fact_funnel_event`

**Row grain.** one row per application per achieved funnel stage (at most 7 rows per application)


**Primary key.** `event_id`


**Purpose.** Event-level ladder of funnel milestones. Prefix-closed and strictly chronological by contract (invariants F1, F2).


**Column count.** 11


| Field | Type | Role | Row grain | Required | Availability at prediction point | Source timestamp | Leakage risk | In feature set | Description | Generation logic | Example / allowed values |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `event_id` | `str` | KEY | one row per application per achieved funnel stage (at most 7 rows per application) | yes | not_applicable | `` | none | — | Funnel event key. | Sequential synthetic key. | FEV-0093112 |
| `application_id` | `str` | KEY | one row per application per achieved funnel stage (at most 7 rows per application) | yes | not_applicable | `` | none | — | Application the milestone belongs to. | FK to fact_application. | APP-0128447 |
| `programme_id` | `str` | KEY | one row per application per achieved funnel stage (at most 7 rows per application) | yes | not_applicable | `` | none | — | Denormalised programme (partition/join key). | Copied from fact_application for panel aggregation without a join. | PGM-07 |
| `cycle_id` | `str` | KEY | one row per application per achieved funnel stage (at most 7 rows per application) | yes | not_applicable | `` | none | — | Denormalised admission cycle (partition key). | Copied from fact_application. | CYC-2024 |
| `stage_code` | `str` | KEY | one row per application per achieved funnel stage (at most 7 rows per application) | yes | not_applicable | `` | none | — | Stage achieved. | FK to dim_funnel_stage. | application_submitted<br>`prospect`, `application_started`, `application_submitted`, `application_verified`, `admission_decision`, `admitted`, `enrolled` |
| `stage_order` | `int64` | DERIVED | one row per application per achieved funnel stage (at most 7 rows per application) | yes | not_applicable | `` | none | — | Integer ladder position of the stage. | Derived: lookup of stage_code in dim_funnel_stage. | 3 |
| `intake_round` | `int64` | DERIVED | one row per application per achieved funnel stage (at most 7 rows per application) | yes | not_applicable | `` | none | — | Intake round of the owning application. | Copied from fact_application. | 1 |
| `event_ts` | `str` | GENERATED | one row per application per achieved funnel stage (at most 7 rows per application) | yes | not_applicable | `` | none | — | Milestone timestamp. | Draw from the stage-specific timing mechanism documented on the corresponding fact_application column. | 2024-07-11T20:14:00 |
| `event_date` | `str` | DERIVED | one row per application per achieved funnel stage (at most 7 rows per application) | yes | not_applicable | `` | none | — | Calendar date of the milestone. | Derived: date part of event_ts. | 2024-07-11 |
| `days_since_prev_stage` | `int64` | DERIVED | one row per application per achieved funnel stage (at most 7 rows per application) | no (nullable) | not_applicable | `` | none | — | Days elapsed since the previous achieved milestone. Null for the first stage. | Derived: floor of the difference between consecutive milestones. | 5 |
| `is_terminal_stage` | `bool` | DERIVED | one row per application per achieved funnel stage (at most 7 rows per application) | yes | not_applicable | `` | none | — | True for the single highest stage the application reached. | Derived: stage_order == stage_reached_order of the application. | False |

---

## `fact_engagement`

**Row grain.** one row per application per activity date, within the pre-submission window


**Primary key.** `engagement_id`


**Purpose.** Daily aggregate of portal activity between the first form session and the prediction point. Exists only for applications that reached `application_started`.


**Column count.** 12


| Field | Type | Role | Row grain | Required | Availability at prediction point | Source timestamp | Leakage risk | In feature set | Description | Generation logic | Example / allowed values |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `engagement_id` | `str` | KEY | one row per application per activity date, within the pre-submission window | yes | not_applicable | `` | none | — | Engagement row key. | Sequential synthetic key. | ENG-0442108 |
| `application_id` | `str` | KEY | one row per application per activity date, within the pre-submission window | yes | not_applicable | `` | none | — | Application the activity belongs to. | FK to fact_application. | APP-0128447 |
| `cycle_id` | `str` | KEY | one row per application per activity date, within the pre-submission window | yes | not_applicable | `` | none | — | Denormalised admission cycle. | Copied from fact_application. | CYC-2024 |
| `activity_date` | `str` | GENERATED | one row per application per activity date, within the pre-submission window | yes | not_applicable | `` | none | — | Date of portal activity. Always on or before date(application_submitted_ts) for submitted applications, which is what makes the derived pre-submission aggregates safe features. | Uniform draw over the active window, conditioned on the latent engagement intensity. | 2024-07-08 |
| `days_before_submission` | `int64` | DERIVED | one row per application per activity date, within the pre-submission window | no (nullable) | not_applicable | `` | none | — | Days between the activity and the prediction point. Null when the application was never submitted (no prediction point exists). | Derived: (date(application_submitted_ts) - activity_date) in days. | 3 |
| `session_count` | `int64` | GENERATED | one row per application per activity date, within the pre-submission window | yes | not_applicable | `` | none | — | Sessions on the activity date. | 1 + Poisson(0.9) on active days, 1 on the first session day. | 2 |
| `total_minutes` | `float64` | GENERATED | one row per application per activity date, within the pre-submission window | yes | not_applicable | `` | none | — | Minutes of activity on the date. | Log-normal around the latent engagement intensity, rounded to 1 dp. | 27.4 |
| `pages_viewed` | `int64` | GENERATED | one row per application per activity date, within the pre-submission window | yes | not_applicable | `` | none | — | Programme pages viewed on the date. | Poisson(2.2) scaled by engagement intensity. | 6 |
| `docs_uploaded` | `int64` | GENERATED | one row per application per activity date, within the pre-submission window | yes | not_applicable | `` | none | — | Documents uploaded on the date. | Poisson(0.5) scaled by engagement intensity, capped at 4. | 1 |
| `form_fields_completed` | `int64` | GENERATED | one row per application per activity date, within the pre-submission window | yes | not_applicable | `` | none | — | Form fields completed on the date. | Poisson(3.5) scaled by engagement intensity, capped at 14. | 9 |
| `device_type` | `str` | GENERATED | one row per application per activity date, within the pre-submission window | yes | not_applicable | `` | none | — | Dominant device for the day's sessions. | Categorical draw with a mobile-heavy base mix. | mobile<br>`mobile`, `desktop`, `tablet` |
| `is_return_visit` | `bool` | GENERATED | one row per application per activity date, within the pre-submission window | yes | not_applicable | `` | none | — | True if the day's sessions were a return to the form rather than the first session. | Deterministic: False on the first activity date, True afterwards. | True |

---

## `fact_forecast_panel`

**Row grain.** one row per programme x admission cycle x ISO week (Monday start)


**Primary key.** `panel_id`


**Purpose.** Regular weekly panel of cumulative funnel counts. This is the forecasting and scenario-simulation surface. Contains no forward-looking column: every value is an as-at-week count.


**Column count.** 24


| Field | Type | Role | Row grain | Required | Availability at prediction point | Source timestamp | Leakage risk | In feature set | Description | Generation logic | Example / allowed values |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `panel_id` | `str` | KEY | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | Panel cell key. | programme_id + cycle_id + week_start_date. | PGM-07\|CYC-2024\|2024-06-03 |
| `programme_id` | `str` | KEY | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | Programme. | FK to dim_programme. | PGM-07 |
| `cycle_id` | `str` | KEY | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | Admission cycle. | FK to dim_admission_cycle. | CYC-2024 |
| `week_start_date` | `str` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | Monday of the ISO week. | Derived: Monday of the week containing the date. | 2024-06-03 |
| `week_end_date` | `str` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | Sunday of the ISO week. | Derived: week_start_date + 6 days. | 2024-06-09 |
| `week_index_in_cycle` | `int64` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | 0-based ISO week index from the cycle start week. | Derived: whole weeks between cycle start week and this week. | 0 |
| `is_forecast_eligible` | `bool` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | True when this week can serve as a forecast origin for the enrolled-yield task: at least 4 weeks of history, on or after the first decision window opens, and on or before the cycle enrolment end date. | Derived from week_index_in_cycle and the cycle calendar. | False |
| `split_hint` | `str` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | Chronological split hint derived only from cycle_id. | Deterministic mapping of sorted cycle_id to train / validation / test. | train<br>`train`, `validation`, `test` |
| `n_applications` | `int64` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | Number of application rows in the cell's programme-cycle, for denominator checks. | Derived: count of fact_application per programme-cycle. | 0 |
| `cum_applications_opened` | `int64` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | Cumulative applications opened (stage `prospect`) as at the end of the week. Derived: running count of the corresponding funnel events whose event_date falls on or before week_end_date. | 742 | — |
| `cum_applications_started` | `int64` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | Cumulative applications started (stage `application_started`) as at the end of the week. Derived: running count of the corresponding funnel events whose event_date falls on or before week_end_date. | 742 | — |
| `cum_applications_submitted` | `int64` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | Cumulative applications submitted (stage `application_submitted`) as at the end of the week. Derived: running count of the corresponding funnel events whose event_date falls on or before week_end_date. | 742 | — |
| `cum_applications_verified` | `int64` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | Cumulative applications verified (stage `application_verified`) as at the end of the week. Derived: running count of the corresponding funnel events whose event_date falls on or before week_end_date. | 742 | — |
| `cum_decisions_issued` | `int64` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | Cumulative decisions released (stage `admission_decision`) as at the end of the week. Derived: running count of the corresponding funnel events whose event_date falls on or before week_end_date. | 742 | — |
| `cum_admitted` | `int64` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | Cumulative admitted (stage `admitted`) as at the end of the week. Derived: running count of the corresponding funnel events whose event_date falls on or before week_end_date. | 742 | — |
| `cum_enrolled` | `int64` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | Cumulative enrolled (stage `enrolled`) as at the end of the week. PRIMARY FORECAST QUANTITY. Derived: running count of the corresponding funnel events whose event_date falls on or before week_end_date. | 742 | — |
| `wk_applications_submitted` | `int64` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | Applications submitted during the week. Derived: count of events whose event_date falls inside [week_start_date, week_end_date]. | 41 | — |
| `wk_applications_verified` | `int64` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | Applications verified during the week. Derived: count of events whose event_date falls inside [week_start_date, week_end_date]. | 41 | — |
| `wk_decisions_issued` | `int64` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | Decisions released during the week. Derived: count of events whose event_date falls inside [week_start_date, week_end_date]. | 41 | — |
| `wk_admitted` | `int64` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | Admitted during the week. Derived: count of events whose event_date falls inside [week_start_date, week_end_date]. | 41 | — |
| `wk_enrolled` | `int64` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | yes | not_applicable | `` | none | — | Enrolled during the week. Derived: count of events whose event_date falls inside [week_start_date, week_end_date]. | 41 | — |
| `cum_submit_to_verify_rate` | `float64` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | no (nullable) | not_applicable | `` | none | — | cum_applications_verified / cum_applications_submitted. NULL while the denominator is zero. | Derived ratio, rounded to 6 dp. | 0.7612 |
| `cum_admit_rate` | `float64` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | no (nullable) | not_applicable | `` | none | — | cum_admitted / cum_decisions_issued. NULL while the denominator is zero. | Derived ratio, rounded to 6 dp. | 0.5127 |
| `cum_enrolment_yield` | `float64` | DERIVED | one row per programme x admission cycle x ISO week (Monday start) | no (nullable) | not_applicable | `` | none | — | cum_enrolled / cum_applications_submitted. The headline yield metric of the project. NULL while the denominator is zero. | Derived ratio, rounded to 6 dp. | 0.2531 |

---

## `applications_modelling_view` (denormalised, `data/processed/`)

Deterministic denormalised extract used for the primary supervised task. Built entirely by the generator from the raw tables; it is not hand-edited. Population: applications that reached `application_submitted`, i.e. rows that have a prediction point.


**Row grain.** one row per application that reached `application_submitted`

**Column count.** 58


| Field | Source | Role | Required | Availability | Leakage risk | In `primary` | In `decision` | Description |
|---|---|---|---|---|---|---|---|---|
| `application_id` | `fact_application.application_id` | KEY | no (nullable) | not_applicable | none | no | no | Synthetic application key. Join key, not a feature. |
| `applicant_id` | `fact_applicant.applicant_id` | KEY | no (nullable) | not_applicable | none | no | no | Synthetic applicant key. Join key, not a feature. |
| `programme_id` | `fact_application.programme_id` | GENERATED | no (nullable) | pre_submission | low | yes | yes | Programme applied to. |
| `cycle_id` | `fact_application.cycle_id` | GENERATED | no (nullable) | pre_submission | low | yes | yes | Admission cycle. |
| `cohort_label` | `fact_application.cohort_label` | DERIVED | no (nullable) | pre_submission | low | yes | yes | Programme x cycle cohort key. |
| `split_hint` | `fact_application.split_hint` | DERIVED | no (nullable) | pre_submission | low | yes | yes | Chronological split hint from cycle_id only. |
| `acquisition_channel` | `fact_application.acquisition_channel` | GENERATED | no (nullable) | pre_submission | low | yes | yes | First-touch acquisition channel (association only, not causal). |
| `acquisition_source` | `fact_application.acquisition_source` | GENERATED | no (nullable) | pre_submission | low | yes | yes | Sub-channel within the acquisition channel. |
| `campaign_id` | `fact_application.campaign_id` | GENERATED | no (nullable) | pre_submission | low | yes | yes | Attributed campaign, null for non-campaign channels. |
| `first_touch_date` | `fact_application.first_touch_date` | GENERATED | no (nullable) | pre_submission | low | yes | yes | First recorded marketing touch date. |
| `touchpoints_count` | `fact_application.touchpoints_count` | GENERATED | no (nullable) | pre_submission | low | yes | yes | Marketing touchpoints before inquiry. |
| `is_multi_touch` | `fact_application.is_multi_touch` | GENERATED | no (nullable) | pre_submission | low | yes | yes | More than one pre-inquiry touchpoint. |
| `is_referral_alumni` | `fact_application.is_referral_alumni` | GENERATED | no (nullable) | pre_submission | low | yes | yes | Referral originated from an alumnus. |
| `region_id` | `fact_applicant.region_id` | GENERATED | no (nullable) | pre_submission | low | yes | yes | Applicant origin region. |
| `region_name` | `dim_region.region_name` | REFERENCE | no (nullable) | pre_submission | low | yes | yes | Region name. |
| `region_type` | `dim_region.region_type` | REFERENCE | no (nullable) | pre_submission | low | yes | yes | Settlement type. |
| `mean_distance_km_to_campus` | `dim_region.mean_distance_km_to_campus` | GENERATED | no (nullable) | pre_submission | low | yes | yes | Mean travel distance to campus; proxy for relocation cost. |
| `gender_band` | `fact_applicant.gender_band` | GENERATED | no (nullable) | pre_submission | low | yes | yes | Synthetic gender band. Segmentation only, never a decision variable. |
| `education_level` | `fact_applicant.education_level` | GENERATED | no (nullable) | pre_submission | low | yes | yes | Highest qualification held at first application. |
| `is_repeat_applicant_at_prediction` | `fact_application.is_repeat_applicant_at_prediction` | DERIVED | no (nullable) | at_prediction_point | low | yes | yes | Applicant already held another submitted application at this prediction point. The leakage-safe version of the lifetime repeat flag. |
| `selectivity_tier` | `dim_programme.selectivity_tier` | REFERENCE | no (nullable) | pre_submission | low | yes | yes | Published selectivity band. |
| `duration_years` | `dim_programme.duration_years` | GENERATED | no (nullable) | pre_submission | low | yes | yes | Programme duration. |
| `annual_fee_inr` | `dim_programme.annual_fee_inr` | GENERATED | no (nullable) | pre_submission | low | yes | yes | Published annual fee. |
| `base_seat_capacity` | `dim_programme.base_seat_capacity` | GENERATED | no (nullable) | pre_submission | low | yes | yes | Approved intake capacity. |
| `review_duration_days` | `dim_programme.review_duration_days` | GENERATED | no (nullable) | pre_submission | low | yes | yes | Median submission-to-verification duration. |
| `demand_weight` | `dim_programme.demand_weight` | GENERATED | no (nullable) | pre_submission | low | yes | yes | Published relative programme attractiveness. |
| `campus_region_id` | `dim_programme.campus_region_id` | GENERATED | no (nullable) | pre_submission | low | yes | yes | Region of the campus. |
| `intake_round` | `fact_application.intake_round` | GENERATED | no (nullable) | pre_submission | low | yes | yes | Intake round. |
| `academic_score_pct` | `fact_application.academic_score_pct` | GENERATED | no (nullable) | at_prediction_point | low | yes | yes | Qualifying examination score, reported at submission. |
| `academic_score_band` | `fact_application.academic_score_band` | DERIVED | no (nullable) | at_prediction_point | low | yes | yes | Banded academic score (from the submission-time score only). |
| `doc_completeness_score` | `fact_application.doc_completeness_score` | GENERATED | no (nullable) | at_prediction_point | low | yes | yes | Document completeness at submission. |
| `fee_scholarship_applied` | `fact_application.fee_scholarship_applied` | GENERATED | no (nullable) | at_prediction_point | low | yes | yes | Fee concession applied for at submission. |
| `inquiry_ts` | `fact_application.inquiry_ts` | GENERATED | no (nullable) | pre_submission | none | yes | yes | Inquiry timestamp. |
| `application_started_ts` | `fact_application.application_started_ts` | GENERATED | no (nullable) | pre_submission | none | yes | yes | First form session timestamp. |
| `application_submitted_ts` | `fact_application.application_submitted_ts` | DERIVED | no (nullable) | at_prediction_point | none | yes | yes | Submission timestamp. THE PREDICTION POINT. |
| `days_inquiry_to_start` | `fact_application.days_inquiry_to_start` | DERIVED | no (nullable) | pre_submission | none | yes | yes | Days from inquiry to first session. |
| `days_start_to_submit` | `fact_application.days_start_to_submit` | DERIVED | no (nullable) | at_prediction_point | none | yes | yes | Days from first session to submission. |
| `days_inquiry_to_submit` | `fact_application.days_inquiry_to_submit` | DERIVED | no (nullable) | at_prediction_point | none | yes | yes | Days from inquiry to submission. |
| `days_to_round_close_at_start` | `fact_application.days_to_round_close_at_start` | DERIVED | no (nullable) | pre_submission | none | yes | yes | Days from first session to the round close date. |
| `week_of_cycle_at_submission` | `fact_application.week_of_cycle_at_submission` | DERIVED | no (nullable) | at_prediction_point | none | yes | yes | ISO week index of submission within the cycle. |
| `month_of_submission` | `fact_application.month_of_submission` | DERIVED | no (nullable) | at_prediction_point | none | yes | yes | Calendar month of submission. |
| `pre_sub_session_count` | `fact_application.pre_sub_session_count` | DERIVED | no (nullable) | pre_submission | none | yes | yes | Pre-submission sessions. |
| `pre_sub_active_days` | `fact_application.pre_sub_active_days` | DERIVED | no (nullable) | pre_submission | none | yes | yes | Distinct pre-submission activity dates. |
| `pre_sub_total_minutes` | `fact_application.pre_sub_total_minutes` | DERIVED | no (nullable) | pre_submission | none | yes | yes | Pre-submission activity minutes. |
| `pre_sub_doc_uploads` | `fact_application.pre_sub_doc_uploads` | DERIVED | no (nullable) | pre_submission | none | yes | yes | Documents uploaded pre-submission. |
| `pre_sub_form_fields_completed` | `fact_application.pre_sub_form_fields_completed` | DERIVED | no (nullable) | pre_submission | none | yes | yes | Form fields completed pre-submission. |
| `pre_sub_return_visits` | `fact_application.pre_sub_return_visits` | DERIVED | no (nullable) | pre_submission | none | yes | yes | Pre-submission return visits. |
| `admission_decision_ts` | `fact_application.admission_decision_ts` | POST_OUTCOME | no (nullable) | post_prediction_point | high | no | no | Decision timestamp. It is the PREDICTION POINT of the secondary decision view, not a feature; never usable for the primary task. |
| `application_verified_ts` | `fact_application.application_verified_ts` | POST_OUTCOME | no (nullable) | post_prediction_point | high | no | yes | Verification timestamp. NOT a primary feature; available at the decision point. |
| `doc_verification_status` | `fact_application.doc_verification_status` | POST_OUTCOME | no (nullable) | post_prediction_point | high | no | yes | Verification outcome. NOT a primary feature; available at the decision point. |
| `doc_query_raised` | `fact_application.doc_query_raised` | POST_OUTCOME | no (nullable) | post_prediction_point | high | no | yes | Document query raised. NOT a primary feature; available at the decision point. |
| `doc_query_count` | `fact_application.doc_query_count` | POST_OUTCOME | no (nullable) | post_prediction_point | high | no | yes | Document query count. NOT a primary feature; available at the decision point. |
| `days_submitted_to_verified` | `fact_application.days_submitted_to_verified` | POST_OUTCOME | no (nullable) | post_prediction_point | high | no | yes | Submission-to-verification days. NOT a primary feature; known at the decision point. |
| `stage_reached` | `fact_application.stage_reached` | POST_OUTCOME | no (nullable) | post_prediction_point | high | no | no | Highest stage reached. POST_OUTCOME. |
| `stage_reached_order` | `fact_application.stage_reached_order` | POST_OUTCOME | no (nullable) | post_prediction_point | high | no | no | Ladder position of stage_reached. POST_OUTCOME. |
| `admitted_flag` | `fact_application.admitted_flag` | POST_OUTCOME | no (nullable) | post_prediction_point | high | no | no | Secondary target for admission-offer prediction. POST_OUTCOME, never a feature of enrolled_flag. |
| `enrolled_given_admitted_flag` | `fact_application.enrolled_given_admitted_flag` | TARGET | no (nullable) | post_prediction_point | high | no | no | Conditional secondary target, predicted at the decision point. |
| `enrolled_flag` | `fact_application.enrolled_flag` | TARGET | no (nullable) | post_prediction_point | high | no | no | PRIMARY TARGET. Registration completed for this programme in this cycle. |

---

## Leakage boundary

### SAFE prediction features — `primary` set

| Table | Field | Source timestamp |
|---|---|---|
| `dim_region` | `mean_distance_km_to_campus` | `inquiry_ts` |
| `dim_region` | `region_inquiry_weight` | `inquiry_ts` |
| `dim_programme` | `duration_years` | `inquiry_ts` |
| `dim_programme` | `annual_fee_inr` | `inquiry_ts` |
| `dim_programme` | `base_seat_capacity` | `inquiry_ts` |
| `dim_programme` | `selectivity_tier` | `inquiry_ts` |
| `dim_programme` | `review_duration_days` | `inquiry_ts` |
| `dim_programme` | `demand_weight` | `inquiry_ts` |
| `dim_programme` | `campus_region_id` | `inquiry_ts` |
| `fact_applicant` | `region_id` | `inquiry_ts` |
| `fact_applicant` | `gender_band` | `inquiry_ts` |
| `fact_applicant` | `education_level` | `inquiry_ts` |
| `fact_applicant` | `application_count` | `inquiry_ts` |
| `fact_application` | `programme_id` | `inquiry_ts` |
| `fact_application` | `cycle_id` | `inquiry_ts` |
| `fact_application` | `campaign_id` | `first_touch_date` |
| `fact_application` | `acquisition_channel` | `first_touch_date` |
| `fact_application` | `acquisition_source` | `first_touch_date` |
| `fact_application` | `first_touch_date` | `first_touch_date` |
| `fact_application` | `touchpoints_count` | `first_touch_date` |
| `fact_application` | `is_multi_touch` | `first_touch_date` |
| `fact_application` | `is_referral_alumni` | `first_touch_date` |
| `fact_application` | `intake_round` | `inquiry_ts` |
| `fact_application` | `academic_score_pct` | `application_submitted_ts` |
| `fact_application` | `academic_score_band` | `application_submitted_ts` |
| `fact_application` | `doc_completeness_score` | `application_submitted_ts` |
| `fact_application` | `fee_scholarship_applied` | `application_submitted_ts` |
| `fact_application` | `is_repeat_applicant_at_prediction` | `application_submitted_ts` |
| `fact_application` | `inquiry_ts` | `inquiry_ts` |
| `fact_application` | `application_started_ts` | `application_started_ts` |
| `fact_application` | `application_submitted_ts` | `application_submitted_ts` |
| `fact_application` | `days_inquiry_to_start` | `application_started_ts` |
| `fact_application` | `days_start_to_submit` | `application_submitted_ts` |
| `fact_application` | `days_inquiry_to_submit` | `application_submitted_ts` |
| `fact_application` | `days_to_round_close_at_start` | `application_started_ts` |
| `fact_application` | `week_of_cycle_at_submission` | `application_submitted_ts` |
| `fact_application` | `month_of_submission` | `application_submitted_ts` |
| `fact_application` | `pre_sub_session_count` | `application_submitted_ts` |
| `fact_application` | `pre_sub_active_days` | `application_submitted_ts` |
| `fact_application` | `pre_sub_total_minutes` | `application_submitted_ts` |
| `fact_application` | `pre_sub_doc_uploads` | `application_submitted_ts` |
| `fact_application` | `pre_sub_form_fields_completed` | `application_submitted_ts` |
| `fact_application` | `pre_sub_return_visits` | `application_submitted_ts` |
| `fact_application` | `cohort_label` | `inquiry_ts` |
| `fact_application` | `split_hint` | `inquiry_ts` |

### POST-OUTCOME / TARGET fields — forbidden as primary features

| Table | Field | Role | Leakage |
|---|---|---|---|
| `fact_application` | `stage_reached` | POST_OUTCOME | `high` |
| `fact_application` | `stage_reached_order` | POST_OUTCOME | `high` |
| `fact_application` | `dropoff_stage` | POST_OUTCOME | `high` |
| `fact_application` | `dropoff_reason` | POST_OUTCOME | `high` |
| `fact_application` | `doc_query_raised` | POST_OUTCOME | `high` |
| `fact_application` | `doc_query_count` | POST_OUTCOME | `high` |
| `fact_application` | `doc_verification_status` | POST_OUTCOME | `high` |
| `fact_application` | `application_verified_ts` | POST_OUTCOME | `high` |
| `fact_application` | `admission_decision_ts` | POST_OUTCOME | `high` |
| `fact_application` | `admitted_ts` | POST_OUTCOME | `high` |
| `fact_application` | `enrolled_ts` | POST_OUTCOME | `high` |
| `fact_application` | `days_submitted_to_verified` | POST_OUTCOME | `high` |
| `fact_application` | `days_verified_to_decision` | POST_OUTCOME | `high` |
| `fact_application` | `days_decision_to_enrolled` | POST_OUTCOME | `high` |
| `fact_application` | `decision_type` | POST_OUTCOME | `high` |
| `fact_application` | `selection_score` | POST_OUTCOME | `high` |
| `fact_application` | `offer_letter_issued` | POST_OUTCOME | `high` |
| `fact_application` | `offer_deadline` | POST_OUTCOME | `high` |
| `fact_application` | `scholarship_offered` | POST_OUTCOME | `high` |
| `fact_application` | `scholarship_amount_inr` | POST_OUTCOME | `high` |
| `fact_application` | `withdrawn_flag` | POST_OUTCOME | `high` |
| `fact_application` | `withdrawn_date` | POST_OUTCOME | `high` |
| `fact_application` | `admitted_flag` | POST_OUTCOME | `high` |
| `fact_application` | `enrolled_given_admitted_flag` | TARGET | `high` |
| `fact_application` | `enrolled_flag` | TARGET | `high` |

> `selection_score` is retained in the raw table **on purpose** (contract decision D-11). It is the most realistic leakage trap an admissions dataset contains: the institution's own merit score, computed at decision time, which does not exist at the prediction point. The validator fails the dataset if it appears in any feature set.


---

## Attribution semantics

`acquisition_channel`, `acquisition_source` and `campaign_id` are **recorded associations, not causal effects**. Differences in conversion between channels arise because channels attract different applicant mixes. No causal, uplift or counterfactual claim is licensed by this dataset.


---

## PII boundary

The dataset contains **no PII**: no names, emails, phone numbers, addresses, dates of birth or government identifiers. `applicant_id` and `application_id` are synthetic surrogate keys. Quasi-identifying attributes are coarse and synthetic (`region_id`, `gender_band`, `education_level`) and exist for segmentation only.


---

The primary project dataset is synthetic and was generated according to the documented AdmitFlow admission-funnel specification for development, experimentation, evaluation, and demonstration. It does not represent any real institution, applicant, or admission outcome.

> Any metric computed on this dataset is a property of the documented generator assumptions. It must never be reported as real-world institutional performance.

