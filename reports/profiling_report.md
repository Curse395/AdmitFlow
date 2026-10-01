# AdmitFlow — Dataset Profiling Report

> The primary project dataset is synthetic and was generated according to the documented AdmitFlow admission-funnel specification for development, experimentation, evaluation, and demonstration. It does not represent any real institution, applicant, or admission outcome.


> This is a descriptive profile of a synthetic dataset. It contains no model performance figures: no fitted model, no train/test score, no accuracy, AUC, precision, recall, RMSE, SHAP value or feature importance. Any such number must come from the downstream modelling step, evaluated on the documented chronological split.


Produced by `scripts/profile_dataset.py` from the generated dataset. The profiler is read-only: it never writes to `data/`.


**Prediction unit:** application  |  **Primary target:** `enrolled_flag`  |  **Forecast grain:** programme x cycle x ISO week


---

## 1. Shape and inventory

| Setting | Value |
|---|---|
| seed | `20240817` |
| dataset_version | `1.0.0` |
| generator config (target n_applications) | 28,000 |
| admission cycles | 4 |
| start cycle year | 2022 |
| forecast horizons (weeks) | [1, 2, 4, 6] |
| numpy / pandas | 2.2.6 / 2.3.3 |

| Table | Grain | Rows | Columns | Target columns |
|---|---|---|---|---|
| `dim_funnel_stage` | one row per admission funnel stage | 7 | 7 | 0 |
| `dim_region` | one row per applicant-origin region | 8 | 5 | 0 |
| `dim_programme` | one row per programme offered by the fictional institution | 12 | 12 | 0 |
| `dim_admission_cycle` | one row per admission cycle | 4 | 20 | 0 |
| `dim_campaign` | one row per marketing campaign within an admission cycle | 32 | 9 | 0 |
| `fact_applicant` | one row per applicant | 25,279 | 7 | 0 |
| `fact_application` | one row per applicant's application journey to one programme in one admission cycle, opened at the prospect stage | 28,000 | 61 | 2 |
| `fact_funnel_event` | one row per application per achieved funnel stage (at most 7 rows per application) | 84,383 | 11 | 0 |
| `fact_engagement` | one row per application per activity date, within the pre-submission window | 38,369 | 12 | 0 |
| `fact_forecast_panel` | one row per programme x admission cycle x ISO week (Monday start) | 2,064 | 24 | 0 |

| Derived view | Grain | Rows | Columns | Target columns |
|---|---|---|---|---|
| `applications_modelling_view` | one submitted application | 12,161 | 58 | 1 primary + 2 secondary |

**Total fact and dimension rows: 178,158.**

---

## 2. Missingness

Nullability is declared per column. A column may be `required` (it belongs to the entity and is always written) yet `nullable` (its value only exists for the subset of rows that reached a given funnel stage). See `STAGE_CONDITIONAL_COLUMNS` in `scripts/admitflow_schema.py` for the population of each such column.

| Column | Null rate | Role | Expected? | Population |
|---|---|---|---|---|
| `fact_application.withdrawn_date` | 99.40% | POST_OUTCOME | conditional | Date of withdrawal. Null when the applicant did not withdraw |
| `fact_application.enrolled_ts` | 87.90% | POST_OUTCOME | conditional | Timestamp at which registration and first fee instalment wer |
| `fact_application.days_decision_to_enrolled` | 87.90% | POST_OUTCOME | conditional | Days from decision to enrolment for admitted applicants. |
| `fact_application.enrolled_given_admitted_flag` | 83.12% | TARGET | conditional | Conditional target: 1 if an ADMITTED applicant went on to en |
| `fact_application.offer_deadline` | 83.12% | POST_OUTCOME | conditional | Last date the offer could be accepted. |
| `fact_application.admitted_ts` | 83.12% | POST_OUTCOME | conditional | Timestamp at which the offer was dispatched and the seat con |
| `fact_application.decision_type` | 64.81% | POST_OUTCOME | conditional | Formal decision released. THE DECISION ITSELF - never a feat |
| `fact_application.selection_score` | 64.81% | POST_OUTCOME | conditional | The institution's internal merit score, computed at decision |
| `fact_application.days_verified_to_decision` | 64.81% | POST_OUTCOME | conditional | Days from verification to decision release. |
| `fact_application.admission_decision_ts` | 64.81% | POST_OUTCOME | conditional | Timestamp at which the decision was released. |
| `fact_application.days_submitted_to_verified` | 64.20% | POST_OUTCOME | conditional | Days from submission to verification. |
| `fact_application.application_verified_ts` | 64.20% | POST_OUTCOME | conditional | Timestamp at which verification was granted. Strictly after  |
| `fact_application.days_inquiry_to_submit` | 56.57% | DERIVED | conditional | null unless the application was submitted |
| `fact_application.academic_score_pct` | 56.57% | GENERATED | conditional | declared on the form at submission; null unless submitted |
| `fact_application.academic_score_band` | 56.57% | DERIVED | conditional | banded from `academic_score_pct`; null unless submitted |
| `fact_application.doc_completeness_score` | 56.57% | GENERATED | conditional | computed from the uploaded set at submission; null unless submitted |
| `fact_application.application_submitted_ts` | 56.57% | DERIVED | conditional | null unless the application reached `application_submitted` |
| `fact_application.prediction_ts` | 56.57% | DERIVED | conditional | the prediction point; null unless the application was submitted |
| `fact_application.pre_sub_form_fields_completed` | 56.57% | DERIVED | conditional | engagement summary; null unless the application was submitted |
| `fact_application.week_of_cycle_at_submission` | 56.57% | DERIVED | conditional | null unless the application was submitted |
| `fact_application.prediction_stage` | 56.57% | DERIVED | conditional | the stage at the prediction point; null unless submitted |
| `fact_application.pre_sub_doc_uploads` | 56.57% | DERIVED | conditional | engagement summary; null unless the application was submitted |
| `fact_application.pre_sub_session_count` | 56.57% | DERIVED | conditional | engagement summary; null unless the application was submitted |
| `fact_application.month_of_submission` | 56.57% | DERIVED | conditional | null unless the application was submitted |
| `fact_application.pre_sub_active_days` | 56.57% | DERIVED | conditional | engagement summary; null unless the application was submitted |
| `fact_application.pre_sub_total_minutes` | 56.57% | DERIVED | conditional | engagement summary; null unless the application was submitted |
| `fact_application.days_start_to_submit` | 56.57% | DERIVED | conditional | null unless the application was submitted |
| `fact_application.pre_sub_return_visits` | 56.57% | DERIVED | conditional | engagement summary; null unless the application was submitted |
| `fact_application.campaign_id` | 55.70% | KEY | conditional | Attributed campaign. Null unless the acquisition channel is  |
| `fact_application.application_started_ts` | 42.04% | GENERATED | conditional | null unless the application reached `application_started` |
| `fact_application.days_to_round_close_at_start` | 42.04% | DERIVED | conditional | null unless the application reached `application_started` |
| `fact_application.days_inquiry_to_start` | 42.04% | DERIVED | conditional | null unless the application reached `application_started` |
| `fact_application.dropoff_stage` | 12.10% | POST_OUTCOME | conditional | Stage at which the application left the funnel. Null when en |
| `fact_application.dropoff_reason` | 12.10% | POST_OUTCOME | conditional | Single categorical reason for leaving the funnel. Null when  |
| `fact_funnel_event.days_since_prev_stage` | 33.18% | DERIVED | conditional | Days elapsed since the previous achieved milestone. Null for |
| `fact_engagement.days_before_submission` | 27.33% | DERIVED | conditional | Days between the activity and the prediction point. Null whe |
| `fact_forecast_panel.cum_admit_rate` | 59.01% | DERIVED | conditional | cum_admitted / cum_decisions_issued. NULL while the denomina |
| `fact_forecast_panel.cum_submit_to_verify_rate` | 9.30% | DERIVED | conditional | cum_applications_verified / cum_applications_submitted. NULL |
| `fact_forecast_panel.cum_enrolment_yield` | 9.30% | DERIVED | conditional | cum_enrolled / cum_applications_submitted. The headline yiel |

Columns omitted from this table have under 0.5% null values. A column that is *conditional* is null exactly for the rows that did not reach the funnel stage it describes - the null pattern is itself the signal, not a data defect.


---

## 3. Duplicates and key integrity

| Table | Primary key | Duplicate keys | Duplicate rows |
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

**Foreign keys.** Every foreign key value must exist in its parent table.

| Child column | Parent column | Orphan values | Status |
|---|---|---|---|
| `dim_programme.campus_region_id` | `dim_region.region_id` | 0 | OK |
| `dim_campaign.cycle_id` | `dim_admission_cycle.cycle_id` | 0 | OK |
| `fact_applicant.region_id` | `dim_region.region_id` | 0 | OK |
| `fact_application.applicant_id` | `fact_applicant.applicant_id` | 0 | OK |
| `fact_application.programme_id` | `dim_programme.programme_id` | 0 | OK |
| `fact_application.cycle_id` | `dim_admission_cycle.cycle_id` | 0 | OK |
| `fact_application.campaign_id` | `dim_campaign.campaign_id` | 0 | OK |
| `fact_funnel_event.application_id` | `fact_application.application_id` | 0 | OK |
| `fact_funnel_event.programme_id` | `dim_programme.programme_id` | 0 | OK |
| `fact_funnel_event.cycle_id` | `dim_admission_cycle.cycle_id` | 0 | OK |
| `fact_funnel_event.stage_code` | `dim_funnel_stage.stage_code` | 0 | OK |
| `fact_engagement.application_id` | `fact_application.application_id` | 0 | OK |
| `fact_engagement.cycle_id` | `dim_admission_cycle.cycle_id` | 0 | OK |
| `fact_forecast_panel.programme_id` | `dim_programme.programme_id` | 0 | OK |
| `fact_forecast_panel.cycle_id` | `dim_admission_cycle.cycle_id` | 0 | OK |

Modelling view: 0 duplicate `application_id` values (12,161 rows, one per submitted application).


---

## 4. Category distributions


**`fact_application.acquisition_channel`** - 8 distinct values, 0 null

| Value | Rows | Share |
|---|---|---|
| `organic_search` | 5,562 | 19.86% |
| `paid_search` | 4,966 | 17.74% |
| `social_media` | 3,791 | 13.54% |
| `referral` | 2,981 | 10.65% |
| `email_campaign` | 2,980 | 10.64% |
| `direct` | 2,674 | 9.55% |
| `education_fair` | 2,533 | 9.05% |
| `partner_agency` | 2,513 | 8.97% |

**`fact_application.acquisition_source`** - 27 distinct values, 0 null

| Value | Rows | Share |
|---|---|---|
| `meta_ads_prospect` | 1,707 | 6.10% |
| `google_ads_brand` | 1,635 | 5.84% |
| `google_ads_generic` | 1,624 | 5.80% |
| `content_blog` | 1,421 | 5.08% |
| `bing_organic` | 1,398 | 4.99% |
| `programme_page` | 1,384 | 4.94% |
| `google_organic` | 1,359 | 4.85% |
| `newsletter_prospectus` | 1,007 | 3.60% |
| `alumni_referral_mail` | 991 | 3.54% |
| `linkedin_organic` | 990 | 3.54% |
| `open_day_invite` | 982 | 3.51% |
| `meta_ads_retarget` | 965 | 3.45% |
| `youtube_organic` | 920 | 3.29% |
| `instagram_organic` | 916 | 3.27% |
| `app_download` | 908 | 3.24% |
| `direct_web` | 886 | 3.16% |
| `walk_in` | 880 | 3.14% |
| `district_career_fair` | 879 | 3.14% |
| `nri_helpdesk` | 852 | 3.04% |
| `college_career_fair` | 844 | 3.01% |
| `education_consultant` | 833 | 2.97% |
| `overseas_counsellor` | 828 | 2.96% |
| `school_fair` | 810 | 2.89% |
| `school_counsellor` | 787 | 2.81% |
| `alumni_referral` | 752 | 2.69% |
| `peer_referral` | 726 | 2.59% |
| `parent_referral` | 716 | 2.56% |

**`fact_application.intake_round`** - 2 distinct values, 0 null

| Value | Rows | Share |
|---|---|---|
| `2` | 16,127 | 57.60% |
| `1` | 11,873 | 42.40% |

**`fact_application.academic_score_band`** - 5 distinct values, 0 null

| Value | Rows | Share |
|---|---|---|
| `(null)` | 15,839 | 56.57% |
| `lt_60` | 6,322 | 22.58% |
| `60_69` | 3,865 | 13.80% |
| `70_79` | 1,649 | 5.89% |
| `80_89` | 302 | 1.08% |
| `90_plus` | 23 | 0.08% |

**`fact_application.cycle_id`** - 4 distinct values, 0 null

| Value | Rows | Share |
|---|---|---|
| `CYC-2024` | 7,081 | 25.29% |
| `CYC-2022` | 7,035 | 25.12% |
| `CYC-2023` | 6,965 | 24.88% |
| `CYC-2025` | 6,919 | 24.71% |

**`dim_programme.selectivity_tier`** - 3 distinct values, 0 null

| Value | Rows | Share |
|---|---|---|
| `emerging` | 5 | 41.67% |
| `medium` | 4 | 33.33% |
| `high` | 3 | 25.00% |

**`fact_applicant.gender_band`** - 3 distinct values, 0 null

| Value | Rows | Share |
|---|---|---|
| `male` | 12,441 | 49.21% |
| `female` | 11,456 | 45.32% |
| `other_or_prefer_not_to_say` | 1,382 | 5.47% |

**`fact_applicant.education_level`** - 4 distinct values, 0 null

| Value | Rows | Share |
|---|---|---|
| `higher_secondary` | 17,526 | 69.33% |
| `undergraduate` | 4,511 | 17.84% |
| `diploma` | 2,824 | 11.17% |
| `other` | 418 | 1.65% |

**`dim_region.region_type`** - 4 distinct values, 0 null

| Value | Rows | Share |
|---|---|---|
| `metro` | 2 | 25.00% |
| `tier2` | 2 | 25.00% |
| `tier3` | 2 | 25.00% |
| `rural_remote` | 2 | 25.00% |

> `acquisition_channel`, `acquisition_source` and `campaign_id` are **attribution** fields. They describe which recorded marketing touch is associated with an application. They are not causal: a channel with a higher enrolment yield is not shown to *cause* enrolment, and no analysis in this dataset supports a causal claim about spend.


---

## 5. Target distribution

| Target | Meaning | Populated rows | Positive rate | Positives | Negatives |
|---|---|---|---|---|---|
| `enrolled_flag` | PRIMARY - registered at the prediction point of submission | 12,161 | 27.86% | 3,388 | 8,773 |
| `admitted_flag` | TERTIARY - received an offer | 12,161 | 38.87% | 4,727 | 7,434 |
| `enrolled_given_admitted_flag` | SECONDARY - registered, among admits | 4,727 | 71.67% | 3,388 | 1,339 |

The primary target `enrolled_flag` has a positive rate of 27.86% over 12,161 submitted applications. That is high enough to model and low enough to still be the minority class, so a classifier is not trivially accurate by always predicting the majority.

**Is the target trivially predictable?**

Single-feature rank-AUC against `enrolled_flag` for the strongest declared safe features. This is a *data quality* screen proving no single column handed the answer over - it is not a model score and must not be read as one.

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
| `duration_years` | 0.586 |
| `selectivity_tier` | 0.570 |
| `pre_sub_total_minutes` | 0.544 |
| `cohort_label` | 0.541 |

The strongest single safe feature reaches rank AUC 0.713. Because this is well below 1.0, the target cannot be recovered from any one column; it has to be predicted from the joint pattern of roughly 45 allowed features plus irreducible noise. Columns such as `selection_score`, `stage_reached` and `admitted_flag` are **not** in this list because they are post-outcome - they are retained in the raw data precisely as leakage traps, and the validator checks that no feature set contains them.


---

## 6. Funnel counts and conversion

| # | Stage code | Stage name | Reached (cumulative) | Step conversion | Top-of-funnel | Cumulative drop-off |
|---|---|---|---|---|---|---|
| 1 | `prospect` | Prospect / inquiry | 28,000 | - | 1.000 | 0 |
| 2 | `application_started` | Application started | 16,230 | 0.580 | 0.580 | 11,770 |
| 3 | `application_submitted` | Application submitted | 12,161 | 0.749 | 0.434 | 15,839 |
| 4 | `application_verified` | Application verified | 10,023 | 0.824 | 0.358 | 17,977 |
| 5 | `admission_decision` | Decision released | 9,854 | 0.983 | 0.352 | 18,146 |
| 6 | `admitted` | Admitted | 4,727 | 0.480 | 0.169 | 23,273 |
| 7 | `enrolled` | Enrolled | 3,388 | 0.717 | 0.121 | 24,612 |

Top-of-funnel is 28,000 prospects; the full ladder to enrolment retains 0.121 of them.

**Where applicants leave, by stage and reason**

| Stage | Reason | Applications | Share of stage exits |
|---|---|---|---|
| `admission_decision` | `below_merit_cutoff` | 3,621 | 0.706 |
| `admission_decision` | `capacity_exhausted` | 535 | 0.104 |
| `admission_decision` | `eligibility_criteria_failed` | 971 | 0.189 |
| `admitted` | `chose_other_institution` | 362 | 0.270 |
| `admitted` | `financial_constraint` | 250 | 0.187 |
| `admitted` | `offer_deadline_lapsed` | 356 | 0.266 |
| `admitted` | `offer_not_accepted` | 371 | 0.277 |
| `application_started` | `deadline_missed` | 1,464 | 0.360 |
| `application_started` | `form_abandoned` | 1,841 | 0.452 |
| `application_started` | `requirements_unclear` | 764 | 0.188 |
| `application_submitted` | `incomplete_documents` | 1,579 | 0.739 |
| `application_submitted` | `ineligible_qualification` | 559 | 0.261 |
| `application_verified` | `accepted_elsewhere_withdrawn` | 73 | 0.432 |
| `application_verified` | `withdrawn_by_applicant` | 96 | 0.568 |
| `prospect` | `browsed_only` | 4,052 | 0.344 |
| `prospect` | `enquiry_closed_unqualified` | 1,855 | 0.158 |
| `prospect` | `no_response` | 5,863 | 0.498 |

Drop-off reasons are drawn from a stage-specific weighted list, so the mix is not uniform across stages - a real funnel has different causes at different steps.


---

## 7. Conversion by programme, cycle and channel


**By programme**

| Segment | Applications | Submit rate | Verify \| submitted | Admit \| decided | Enrol \| decided | Enrol yield (all apps) |
|---|---|---|---|---|---|---|
| `PGM-01` | 3,682 | 0.430 | 0.832 | 0.304 | 0.203 | 0.071 |
| `PGM-02` | 4,432 | 0.431 | 0.818 | 0.298 | 0.190 | 0.066 |
| `PGM-03` | 3,147 | 0.439 | 0.832 | 0.464 | 0.321 | 0.115 |
| `PGM-04` | 1,475 | 0.445 | 0.809 | 0.524 | 0.386 | 0.137 |
| `PGM-05` | 1,813 | 0.450 | 0.848 | 0.294 | 0.199 | 0.074 |
| `PGM-06` | 1,054 | 0.425 | 0.866 | 0.599 | 0.474 | 0.173 |
| `PGM-07` | 3,343 | 0.433 | 0.817 | 0.667 | 0.504 | 0.176 |
| `PGM-08` | 2,753 | 0.448 | 0.816 | 0.430 | 0.305 | 0.109 |
| `PGM-09` | 2,650 | 0.426 | 0.821 | 0.667 | 0.507 | 0.175 |
| `PGM-10` | 1,435 | 0.420 | 0.799 | 0.679 | 0.464 | 0.152 |
| `PGM-11` | 860 | 0.429 | 0.829 | 0.706 | 0.521 | 0.184 |
| `PGM-12` | 1,356 | 0.431 | 0.821 | 0.645 | 0.479 | 0.166 |

**By admission cycle**

| Segment | Applications | Submit rate | Verify \| submitted | Admit \| decided | Enrol \| decided | Enrol yield (all apps) |
|---|---|---|---|---|---|---|
| `CYC-2022` | 7,035 | 0.445 | 0.826 | 0.507 | 0.368 | 0.133 |
| `CYC-2023` | 6,965 | 0.434 | 0.817 | 0.497 | 0.356 | 0.124 |
| `CYC-2024` | 7,081 | 0.425 | 0.827 | 0.456 | 0.328 | 0.113 |
| `CYC-2025` | 6,919 | 0.434 | 0.827 | 0.458 | 0.323 | 0.114 |

**By first-touch acquisition channel**

| Segment | Applications | Submit rate | Verify \| submitted | Admit \| decided | Enrol \| decided | Enrol yield (all apps) |
|---|---|---|---|---|---|---|
| `direct` | 2,674 | 0.456 | 0.828 | 0.478 | 0.347 | 0.129 |
| `education_fair` | 2,533 | 0.429 | 0.841 | 0.492 | 0.342 | 0.122 |
| `email_campaign` | 2,980 | 0.442 | 0.815 | 0.475 | 0.349 | 0.124 |
| `organic_search` | 5,562 | 0.487 | 0.811 | 0.474 | 0.352 | 0.136 |
| `paid_search` | 4,966 | 0.392 | 0.832 | 0.489 | 0.334 | 0.107 |
| `partner_agency` | 2,513 | 0.372 | 0.833 | 0.492 | 0.368 | 0.113 |
| `referral` | 2,981 | 0.529 | 0.803 | 0.478 | 0.359 | 0.150 |
| `social_media` | 3,791 | 0.362 | 0.849 | 0.467 | 0.303 | 0.092 |

**Association only.** Programme mix, cycle mix and applicant composition differ across channels, so a channel-level yield gap is confounded. These numbers must not be read as a marketing effect.


**By intake round**

| Segment | Applications | Submit rate | Verify \| submitted | Admit \| decided | Enrol \| decided | Enrol yield (all apps) |
|---|---|---|---|---|---|---|
| `1` | 11,873 | 0.428 | 0.829 | 0.481 | 0.341 | 0.119 |
| `2` | 16,127 | 0.439 | 0.821 | 0.479 | 0.346 | 0.123 |

---

## 8. Numerical summaries

| Column | n | mean | sd | p25 | p50 | p75 | min | max |
|---|---|---|---|---|---|---|---|---|
| `academic_score_pct` | 12,161 | 59.547 | 10.367 | 52.200 | 59.400 | 66.700 | 40.000 | 99.000 |
| `admitted_flag` | 12,161 | 0.389 | 0.487 | 0.000 | 0.000 | 1.000 | 0.000 | 1.000 |
| `annual_fee_inr` | 12,161 | 131520.928 | 37028.062 | 101000.000 | 122000.000 | 167500.000 | 74000.000 | 195500.000 |
| `base_seat_capacity` | 12,161 | 96.034 | 30.417 | 75.000 | 90.000 | 120.000 | 45.000 | 150.000 |
| `days_inquiry_to_start` | 12,161 | 3.383 | 2.623 | 2.000 | 3.000 | 5.000 | 0.000 | 25.000 |
| `days_inquiry_to_submit` | 12,161 | 7.217 | 3.631 | 5.000 | 7.000 | 9.000 | 0.000 | 32.000 |
| `days_start_to_submit` | 12,161 | 3.835 | 2.589 | 2.000 | 3.000 | 5.000 | 0.000 | 22.000 |
| `days_submitted_to_verified` | 10,023 | 7.020 | 3.926 | 4.000 | 6.000 | 8.000 | 1.000 | 39.000 |
| `days_to_round_close_at_start` | 12,161 | 44.960 | 23.440 | 28.000 | 39.000 | 59.000 | 0.000 | 124.000 |
| `demand_weight` | 12,161 | 0.102 | 0.038 | 0.066 | 0.114 | 0.133 | 0.031 | 0.156 |
| `doc_completeness_score` | 12,161 | 0.770 | 0.197 | 0.662 | 0.819 | 0.923 | 0.150 | 1.000 |
| `doc_query_count` | 12,161 | 0.223 | 0.573 | 0.000 | 0.000 | 0.000 | 0.000 | 4.000 |
| `duration_years` | 12,161 | 3.287 | 0.453 | 3.000 | 3.000 | 4.000 | 3.000 | 4.000 |
| `enrolled_flag` | 12,161 | 0.279 | 0.448 | 0.000 | 0.000 | 1.000 | 0.000 | 1.000 |
| `enrolled_given_admitted_flag` | 4,727 | 0.717 | 0.451 | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |
| `intake_round` | 12,161 | 1.582 | 0.493 | 1.000 | 2.000 | 2.000 | 1.000 | 2.000 |
| `mean_distance_km_to_campus` | 12,161 | 543.987 | 330.768 | 241.119 | 630.707 | 725.749 | 185.996 | 1301.549 |
| `month_of_submission` | 12,161 | 9.882 | 1.733 | 8.000 | 11.000 | 11.000 | 6.000 | 12.000 |
| `pre_sub_active_days` | 12,161 | 2.293 | 1.155 | 1.000 | 2.000 | 3.000 | 1.000 | 8.000 |
| `pre_sub_doc_uploads` | 12,161 | 1.408 | 1.379 | 0.000 | 1.000 | 2.000 | 0.000 | 10.000 |
| `pre_sub_form_fields_completed` | 12,161 | 10.109 | 5.745 | 6.000 | 9.000 | 14.000 | 0.000 | 42.000 |
| `pre_sub_return_visits` | 12,161 | 1.293 | 1.155 | 0.000 | 1.000 | 2.000 | 0.000 | 7.000 |
| `pre_sub_session_count` | 12,161 | 3.663 | 2.487 | 2.000 | 3.000 | 5.000 | 1.000 | 16.000 |
| `pre_sub_total_minutes` | 12,161 | 62.215 | 52.358 | 24.900 | 48.800 | 83.400 | 1.000 | 411.500 |
| `review_duration_days` | 12,161 | 5.730 | 1.536 | 4.141 | 6.249 | 7.326 | 3.370 | 7.914 |
| `stage_reached_order` | 12,161 | 5.302 | 1.360 | 5.000 | 5.000 | 7.000 | 3.000 | 7.000 |
| `touchpoints_count` | 12,161 | 3.291 | 1.652 | 2.000 | 3.000 | 4.000 | 1.000 | 12.000 |
| `week_of_cycle_at_submission` | 12,161 | 18.615 | 7.442 | 11.000 | 23.000 | 25.000 | 2.000 | 28.000 |

Numeric summaries of the primary safe features, computed on the submitted-application population. None of these distributions is degenerate, and no single one separates the target (section 5).

**Pre-submission engagement depth** (only applications that started a form)

| Engagement feature | mean | median | p95 |
|---|---|---|---|
| `pre_sub_session_count` | 3.66 | 3.0 | 8.0 |
| `pre_sub_active_days` | 2.29 | 2.0 | 4.0 |
| `pre_sub_total_minutes` | 62.22 | 48.8 | 168.9 |
| `pre_sub_doc_uploads` | 1.41 | 1.0 | 4.0 |
| `pre_sub_return_visits` | 1.29 | 1.0 | 3.0 |

38,369 engagement rows across 16,230 started applications (2.36 activity days per started application).


---

## 9. Temporal coverage and forecast panel

| Cycle | Start | End | Weeks | Submissions | Submission window |
|---|---|---|---|---|---|
| `CYC-2022` | 2022-06-01 | 2023-03-20 | 43 | 3,134 | 2022-06-17 .. 2022-12-20 |
| `CYC-2023` | 2023-06-01 | 2024-03-20 | 43 | 3,020 | 2023-06-17 .. 2023-12-20 |
| `CYC-2024` | 2024-06-01 | 2025-03-20 | 43 | 3,006 | 2024-06-20 .. 2024-12-20 |
| `CYC-2025` | 2025-06-01 | 2026-03-20 | 43 | 3,001 | 2025-06-22 .. 2025-12-20 |

**Total temporal coverage: 2022-06-10 to 2026-02-26 (44 months) across 4 fully closed cycles.** Every cycle is finalised - decisions released, offers issued and registration closed - so no cycle is right-censored and the last cycle is safe to use as a test period.


**Forecast panel** - grain: one row per programme x cycle x ISO week

| Property | Value |
|---|---|
| Panel rows (programme x cycle x week) | 2,064 |
| Programmes x cycles | 12 x 4 |
| Eligible forecast origins | 552 |
| Horizons H (weeks) | 1, 2, 4, 6 |
| Forecast target | `cum_enrolled` at origin + H (cumulative) |
| Weekly increments available | `wk_applications_submitted`, `wk_applications_verified`, `wk_decisions_issued`, `wk_admitted`, `wk_enrolled` |

The panel is a complete grid: 12 programmes x 4 cycles x ~43 weeks. Cumulative counts are non-increasing down the ladder at every cell and reconcile exactly with `fact_application`, so the panel can be used directly for scenario simulation without re-deriving it from the event table.


**Chronological split**

| Cycle | split_hint |
|---|---|
| `CYC-2022` | `train` |
| `CYC-2023` | `train` |
| `CYC-2024` | `validation` |
| `CYC-2025` | `test` |

`split_hint` is a pure function of `cycle_id` (the split is chronological, never random), so a train/validation/test split can never leak future cycles into training. All cycles are finalised.


---

## 10. Synthetic-data fidelity and leakage boundary

The primary project dataset is synthetic and was generated according to the documented AdmitFlow admission-funnel specification for development, experimentation, evaluation, and demonstration. It does not represent any real institution, applicant, or admission outcome.


**No real personal data.** All names, identifiers, phone numbers and email addresses in this dataset are generated by the pipeline from random draws. There is no link to any real applicant, institution or campaign.


**Attribution fields are non-causal.** `acquisition_channel`, `acquisition_source`, `campaign_id`, `touchpoints_count` and `is_multi_touch` record which marketing touch an application is *associated* with. They support cross-source comparison of volumes and conversion. They do not support a claim that any channel caused any outcome.


**Leakage boundary.** Columns are classified in the data dictionary as GENERATED, DERIVED, TARGET or POST_OUTCOME. The safe prediction features are an explicit allow-list; anything dated after the prediction point is POST_OUTCOME and excluded by construction.

| Feature set | Safe features | POST_OUTCOME members | Prediction point |
|---|---|---|---|
| `primary` | 45 | none | `application_submitted_ts` |
| `decision` | 45 | none | `admission_decision_ts` |

The raw fact table deliberately *retains* 5 post-outcome fields (`selection_score`, `stage_reached`, `admitted_flag`, `application_verified_ts`, `enrolled_ts`) so that a leakage mistake is possible and therefore detectable. `scripts/validate_dataset.py` fails the dataset if any of them reaches a feature set or the modelling view.


**Noise and overlap.** Conversion is driven by latent factors (ability, intent, financial constraint, competing offer) that are only *partially* observed through the recorded columns, plus per-programme merit cutoffs that tighten as applications per seat rise. The residual is irreducible, so the target cannot be recovered exactly even with the true generator parameters.


---


> The primary project dataset is synthetic and was generated according to the documented AdmitFlow admission-funnel specification for development, experimentation, evaluation, and demonstration. It does not represent any real institution, applicant, or admission outcome.

>
> Any metric computed on this dataset is a property of the documented generator assumptions. It must never be reported as real-world institutional performance.

