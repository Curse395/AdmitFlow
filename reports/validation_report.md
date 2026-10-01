# AdmitFlow — Dataset Validation Report

> The primary project dataset is synthetic and was generated according to the documented AdmitFlow admission-funnel specification for development, experimentation, evaluation, and demonstration. It does not represent any real institution, applicant, or admission outcome.


This report is produced by `scripts/validate_dataset.py` and is fully reproducible from the generated dataset. No result in this report is a model performance claim.


**Overall status: PASS** (436 pass, 0 warn, 0 fail, 436 checks)


## Dataset under test

| Setting | Value |
|---|---|
| dataset_version | `1.0.0` |
| seed | `20240817` |
| n_applications (target) | 28,000 |
| admission cycles | 4 (from AY2022) |
| numpy / pandas | 2.2.6 / 2.3.3 |

| Table | Rows | Columns |
|---|---|---|
| `dim_funnel_stage` | 7 | |
| `dim_region` | 8 | |
| `dim_programme` | 12 | |
| `dim_admission_cycle` | 4 | |
| `dim_campaign` | 32 | |
| `fact_applicant` | 25,279 | |
| `fact_application` | 28,000 | |
| `fact_funnel_event` | 84,383 | |
| `fact_engagement` | 38,369 | |
| `fact_forecast_panel` | 2,064 | |
| `applications_modelling_view` | 12,161 | |

---

## STRUCTURAL

_153 checks — 0 fail, 0 warn_


| Check | Status | Detail |
|---|---|---|
| `dim_admission_cycle.columns` | **PASS** | 20 columns present, order-independent |
| `dim_admission_cycle.cycle_end_date.date` | **PASS** | ISO date |
| `dim_admission_cycle.cycle_start_date.date` | **PASS** | ISO date |
| `dim_admission_cycle.intake1_application_close.date` | **PASS** | ISO date |
| `dim_admission_cycle.intake1_application_open.date` | **PASS** | ISO date |
| `dim_admission_cycle.intake1_decision_end.date` | **PASS** | ISO date |
| `dim_admission_cycle.intake1_decision_start.date` | **PASS** | ISO date |
| `dim_admission_cycle.intake1_enrolment_end.date` | **PASS** | ISO date |
| `dim_admission_cycle.intake1_offer_deadline.date` | **PASS** | ISO date |
| `dim_admission_cycle.intake2_application_close.date` | **PASS** | ISO date |
| `dim_admission_cycle.intake2_application_open.date` | **PASS** | ISO date |
| `dim_admission_cycle.intake2_decision_end.date` | **PASS** | ISO date |
| `dim_admission_cycle.intake2_decision_start.date` | **PASS** | ISO date |
| `dim_admission_cycle.intake2_enrolment_end.date` | **PASS** | ISO date |
| `dim_admission_cycle.intake2_offer_deadline.date` | **PASS** | ISO date |
| `dim_admission_cycle.is_finalised.bool` | **PASS** | boolean values |
| `dim_admission_cycle.pk_notnull[cycle_id]` | **PASS** | no null primary keys |
| `dim_admission_cycle.pk_unique[cycle_id]` | **PASS** | 4 unique / 4 rows |
| `dim_admission_cycle.row_count` | **PASS** | 4 rows matches manifest |
| `dim_admission_cycle.total_seats_offers.int` | **PASS** | integral numeric |
| `dim_admission_cycle.total_weeks.int` | **PASS** | integral numeric |
| `dim_admission_cycle.verification_end_date.date` | **PASS** | ISO date |
| `dim_campaign.columns` | **PASS** | 9 columns present, order-independent |
| `dim_campaign.end_date.date` | **PASS** | ISO date |
| `dim_campaign.is_active.bool` | **PASS** | boolean values |
| `dim_campaign.pk_notnull[campaign_id]` | **PASS** | no null primary keys |
| `dim_campaign.pk_unique[campaign_id]` | **PASS** | 32 unique / 32 rows |
| `dim_campaign.planned_budget_inr.int` | **PASS** | integral numeric |
| `dim_campaign.row_count` | **PASS** | 32 rows matches manifest |
| `dim_campaign.start_date.date` | **PASS** | ISO date |
| `dim_funnel_stage.allows_reentry.bool` | **PASS** | boolean values |
| `dim_funnel_stage.columns` | **PASS** | 7 columns present, order-independent |
| `dim_funnel_stage.pk_notnull[stage_code]` | **PASS** | no null primary keys |
| `dim_funnel_stage.pk_unique[stage_code]` | **PASS** | 7 unique / 7 rows |
| `dim_funnel_stage.requires_all_prior_stages.bool` | **PASS** | boolean values |
| `dim_funnel_stage.row_count` | **PASS** | 7 rows matches manifest |
| `dim_funnel_stage.stage_order.int` | **PASS** | integral numeric |
| `dim_programme.annual_fee_inr.int` | **PASS** | integral numeric |
| `dim_programme.base_seat_capacity.int` | **PASS** | integral numeric |
| `dim_programme.columns` | **PASS** | 12 columns present, order-independent |
| `dim_programme.demand_weight.float` | **PASS** | numeric |
| `dim_programme.duration_years.int` | **PASS** | integral numeric |
| `dim_programme.pk_notnull[programme_id]` | **PASS** | no null primary keys |
| `dim_programme.pk_unique[programme_id]` | **PASS** | 12 unique / 12 rows |
| `dim_programme.review_duration_days.float` | **PASS** | numeric |
| `dim_programme.row_count` | **PASS** | 12 rows matches manifest |
| `dim_region.columns` | **PASS** | 5 columns present, order-independent |
| `dim_region.mean_distance_km_to_campus.float` | **PASS** | numeric |
| `dim_region.pk_notnull[region_id]` | **PASS** | no null primary keys |
| `dim_region.pk_unique[region_id]` | **PASS** | 8 unique / 8 rows |
| `dim_region.region_inquiry_weight.float` | **PASS** | numeric |
| `dim_region.row_count` | **PASS** | 8 rows matches manifest |
| `fact_applicant.application_count.int` | **PASS** | integral numeric |
| `fact_applicant.columns` | **PASS** | 7 columns present, order-independent |
| `fact_applicant.first_inquiry_date.date` | **PASS** | ISO date |
| `fact_applicant.is_repeat_applicant.bool` | **PASS** | boolean values |
| `fact_applicant.pk_notnull[applicant_id]` | **PASS** | no null primary keys |
| `fact_applicant.pk_unique[applicant_id]` | **PASS** | 25,279 unique / 25,279 rows |
| `fact_applicant.row_count` | **PASS** | 25,279 rows matches manifest |
| `fact_application.academic_score_pct.float` | **PASS** | numeric |
| `fact_application.admitted_flag.int` | **PASS** | integral numeric |
| `fact_application.columns` | **PASS** | 61 columns present, order-independent |
| `fact_application.days_decision_to_enrolled.int` | **PASS** | integral numeric |
| `fact_application.days_inquiry_to_start.int` | **PASS** | integral numeric |
| `fact_application.days_inquiry_to_submit.int` | **PASS** | integral numeric |
| `fact_application.days_start_to_submit.int` | **PASS** | integral numeric |
| `fact_application.days_submitted_to_verified.int` | **PASS** | integral numeric |
| `fact_application.days_to_round_close_at_start.int` | **PASS** | integral numeric |
| `fact_application.days_verified_to_decision.int` | **PASS** | integral numeric |
| `fact_application.doc_completeness_score.float` | **PASS** | numeric |
| `fact_application.doc_query_count.int` | **PASS** | integral numeric |
| `fact_application.doc_query_raised.bool` | **PASS** | boolean values |
| `fact_application.enrolled_flag.int` | **PASS** | integral numeric |
| `fact_application.enrolled_given_admitted_flag.int` | **PASS** | integral numeric |
| `fact_application.fee_scholarship_applied.bool` | **PASS** | boolean values |
| `fact_application.intake_round.int` | **PASS** | integral numeric |
| `fact_application.is_multi_touch.bool` | **PASS** | boolean values |
| `fact_application.is_referral_alumni.bool` | **PASS** | boolean values |
| `fact_application.is_repeat_applicant_at_prediction.bool` | **PASS** | boolean values |
| `fact_application.month_of_submission.int` | **PASS** | integral numeric |
| `fact_application.offer_letter_issued.bool` | **PASS** | boolean values |
| `fact_application.pk_notnull[application_id]` | **PASS** | no null primary keys |
| `fact_application.pk_unique[application_id]` | **PASS** | 28,000 unique / 28,000 rows |
| `fact_application.pre_sub_active_days.int` | **PASS** | integral numeric |
| `fact_application.pre_sub_doc_uploads.int` | **PASS** | integral numeric |
| `fact_application.pre_sub_form_fields_completed.int` | **PASS** | integral numeric |
| `fact_application.pre_sub_return_visits.int` | **PASS** | integral numeric |
| `fact_application.pre_sub_session_count.int` | **PASS** | integral numeric |
| `fact_application.pre_sub_total_minutes.float` | **PASS** | numeric |
| `fact_application.row_count` | **PASS** | 28,000 rows matches manifest |
| `fact_application.scholarship_amount_inr.int` | **PASS** | integral numeric |
| `fact_application.scholarship_offered.bool` | **PASS** | boolean values |
| `fact_application.selection_score.float` | **PASS** | numeric |
| `fact_application.stage_reached_order.int` | **PASS** | integral numeric |
| `fact_application.touchpoints_count.int` | **PASS** | integral numeric |
| `fact_application.week_of_cycle_at_submission.int` | **PASS** | integral numeric |
| `fact_application.withdrawn_flag.bool` | **PASS** | boolean values |
| `fact_engagement.columns` | **PASS** | 12 columns present, order-independent |
| `fact_engagement.days_before_submission.int` | **PASS** | integral numeric |
| `fact_engagement.docs_uploaded.int` | **PASS** | integral numeric |
| `fact_engagement.form_fields_completed.int` | **PASS** | integral numeric |
| `fact_engagement.is_return_visit.bool` | **PASS** | boolean values |
| `fact_engagement.pages_viewed.int` | **PASS** | integral numeric |
| `fact_engagement.pk_notnull[engagement_id]` | **PASS** | no null primary keys |
| `fact_engagement.pk_unique[engagement_id]` | **PASS** | 38,369 unique / 38,369 rows |
| `fact_engagement.row_count` | **PASS** | 38,369 rows matches manifest |
| `fact_engagement.session_count.int` | **PASS** | integral numeric |
| `fact_engagement.total_minutes.float` | **PASS** | numeric |
| `fact_forecast_panel.columns` | **PASS** | 24 columns present, order-independent |
| `fact_forecast_panel.cum_admit_rate.float` | **PASS** | numeric |
| `fact_forecast_panel.cum_admitted.int` | **PASS** | integral numeric |
| `fact_forecast_panel.cum_applications_opened.int` | **PASS** | integral numeric |
| `fact_forecast_panel.cum_applications_started.int` | **PASS** | integral numeric |
| `fact_forecast_panel.cum_applications_submitted.int` | **PASS** | integral numeric |
| `fact_forecast_panel.cum_applications_verified.int` | **PASS** | integral numeric |
| `fact_forecast_panel.cum_decisions_issued.int` | **PASS** | integral numeric |
| `fact_forecast_panel.cum_enrolled.int` | **PASS** | integral numeric |
| `fact_forecast_panel.cum_enrolment_yield.float` | **PASS** | numeric |
| `fact_forecast_panel.cum_submit_to_verify_rate.float` | **PASS** | numeric |
| `fact_forecast_panel.is_forecast_eligible.bool` | **PASS** | boolean values |
| `fact_forecast_panel.n_applications.int` | **PASS** | integral numeric |
| `fact_forecast_panel.pk_notnull[panel_id]` | **PASS** | no null primary keys |
| `fact_forecast_panel.pk_unique[panel_id]` | **PASS** | 2,064 unique / 2,064 rows |
| `fact_forecast_panel.row_count` | **PASS** | 2,064 rows matches manifest |
| `fact_forecast_panel.week_index_in_cycle.int` | **PASS** | integral numeric |
| `fact_forecast_panel.wk_admitted.int` | **PASS** | integral numeric |
| `fact_forecast_panel.wk_applications_submitted.int` | **PASS** | integral numeric |
| `fact_forecast_panel.wk_applications_verified.int` | **PASS** | integral numeric |
| `fact_forecast_panel.wk_decisions_issued.int` | **PASS** | integral numeric |
| `fact_forecast_panel.wk_enrolled.int` | **PASS** | integral numeric |
| `fact_funnel_event.columns` | **PASS** | 11 columns present, order-independent |
| `fact_funnel_event.days_since_prev_stage.int` | **PASS** | integral numeric |
| `fact_funnel_event.intake_round.int` | **PASS** | integral numeric |
| `fact_funnel_event.is_terminal_stage.bool` | **PASS** | boolean values |
| `fact_funnel_event.pk_notnull[event_id]` | **PASS** | no null primary keys |
| `fact_funnel_event.pk_unique[event_id]` | **PASS** | 84,383 unique / 84,383 rows |
| `fact_funnel_event.row_count` | **PASS** | 84,383 rows matches manifest |
| `fact_funnel_event.stage_order.int` | **PASS** | integral numeric |
| `fk[dim_campaign.cycle_id -> dim_admission_cycle.cycle_id]` | **PASS** | all non-null foreign keys resolve |
| `fk[dim_programme.campus_region_id -> dim_region.region_id]` | **PASS** | all non-null foreign keys resolve |
| `fk[fact_applicant.region_id -> dim_region.region_id]` | **PASS** | all non-null foreign keys resolve |
| `fk[fact_application.applicant_id -> fact_applicant.applicant_id]` | **PASS** | all non-null foreign keys resolve |
| `fk[fact_application.campaign_id -> dim_campaign.campaign_id]` | **PASS** | all non-null foreign keys resolve |
| `fk[fact_application.cycle_id -> dim_admission_cycle.cycle_id]` | **PASS** | all non-null foreign keys resolve |
| `fk[fact_application.programme_id -> dim_programme.programme_id]` | **PASS** | all non-null foreign keys resolve |
| `fk[fact_engagement.application_id -> fact_application.application_id]` | **PASS** | all non-null foreign keys resolve |
| `fk[fact_engagement.cycle_id -> dim_admission_cycle.cycle_id]` | **PASS** | all non-null foreign keys resolve |
| `fk[fact_forecast_panel.cycle_id -> dim_admission_cycle.cycle_id]` | **PASS** | all non-null foreign keys resolve |
| `fk[fact_forecast_panel.programme_id -> dim_programme.programme_id]` | **PASS** | all non-null foreign keys resolve |
| `fk[fact_funnel_event.application_id -> fact_application.application_id]` | **PASS** | all non-null foreign keys resolve |
| `fk[fact_funnel_event.cycle_id -> dim_admission_cycle.cycle_id]` | **PASS** | all non-null foreign keys resolve |
| `fk[fact_funnel_event.programme_id -> dim_programme.programme_id]` | **PASS** | all non-null foreign keys resolve |
| `fk[fact_funnel_event.stage_code -> dim_funnel_stage.stage_code]` | **PASS** | all non-null foreign keys resolve |

---

## DATA

_92 checks — 0 fail, 0 warn_


| Check | Status | Detail |
|---|---|---|
| `attribution.first_touch_le_inquiry` | **PASS** | first_touch_date <= inquiry date for every application |
| `campaign.attribution_coverage` | **PASS** | 6.6% of campaign-channel rows are un-attributed (expected, no campaign was live on the touch date) |
| `campaign.channel_consistency` | **PASS** | campaign_id only appears on campaign-bearing channels |
| `dim_admission_cycle.no_full_row_duplicates` | **PASS** | no duplicated rows |
| `dim_campaign.channel.domain` | **PASS** | 4 values within the declared domain |
| `dim_campaign.no_full_row_duplicates` | **PASS** | no duplicated rows |
| `dim_campaign.target_group.domain` | **PASS** | 4 values within the declared domain |
| `dim_funnel_stage.no_full_row_duplicates` | **PASS** | no duplicated rows |
| `dim_funnel_stage.stage_code.domain` | **PASS** | 7 values within the declared domain |
| `dim_funnel_stage.stage_kind.domain` | **PASS** | 1 values within the declared domain |
| `dim_programme.award_level.domain` | **PASS** | 1 values within the declared domain |
| `dim_programme.faculty.domain` | **PASS** | 5 values within the declared domain |
| `dim_programme.no_full_row_duplicates` | **PASS** | no duplicated rows |
| `dim_programme.selectivity_tier.domain` | **PASS** | 3 values within the declared domain |
| `dim_region.no_full_row_duplicates` | **PASS** | no duplicated rows |
| `dim_region.region_type.domain` | **PASS** | 4 values within the declared domain |
| `fact_applicant.education_level.domain` | **PASS** | 4 values within the declared domain |
| `fact_applicant.gender_band.domain` | **PASS** | 3 values within the declared domain |
| `fact_applicant.no_full_row_duplicates` | **PASS** | no duplicated rows |
| `fact_application.academic_score_band.domain` | **PASS** | 5 values within the declared domain |
| `fact_application.academic_score_band.missingness` | **PASS** | 56.57% null  (stage-conditional: banded from `academic_score_pct`; null unless submitted) |
| `fact_application.academic_score_pct.missingness` | **PASS** | 56.57% null  (stage-conditional: declared on the form at submission; null unless submitted) |
| `fact_application.academic_score_pct.range` | **PASS** | all values within [0.0, 100.0] |
| `fact_application.acquisition_channel.domain` | **PASS** | 8 values within the declared domain |
| `fact_application.acquisition_source.domain` | **PASS** | 27 values within the declared domain |
| `fact_application.admission_decision_ts.missingness` | **PASS** | 64.81% null |
| `fact_application.admitted_flag.binary` | **PASS** | values in {0, 1} |
| `fact_application.admitted_ts.missingness` | **PASS** | 83.12% null |
| `fact_application.application_started_ts.missingness` | **PASS** | 42.04% null  (stage-conditional: null unless the application reached `application_started`) |
| `fact_application.application_submitted_ts.missingness` | **PASS** | 56.57% null  (stage-conditional: null unless the application reached `application_submitted`) |
| `fact_application.application_verified_ts.missingness` | **PASS** | 64.20% null |
| `fact_application.campaign_id.missingness` | **PASS** | 55.70% null |
| `fact_application.days_decision_to_enrolled.missingness` | **PASS** | 87.90% null |
| `fact_application.days_inquiry_to_start.missingness` | **PASS** | 42.04% null  (stage-conditional: null unless the application reached `application_started`) |
| `fact_application.days_inquiry_to_submit.missingness` | **PASS** | 56.57% null  (stage-conditional: null unless the application was submitted) |
| `fact_application.days_start_to_submit.missingness` | **PASS** | 56.57% null  (stage-conditional: null unless the application was submitted) |
| `fact_application.days_submitted_to_verified.missingness` | **PASS** | 64.20% null |
| `fact_application.days_to_round_close_at_start.missingness` | **PASS** | 42.04% null  (stage-conditional: null unless the application reached `application_started`) |
| `fact_application.days_verified_to_decision.missingness` | **PASS** | 64.81% null |
| `fact_application.decision_type.domain` | **PASS** | 2 values within the declared domain |
| `fact_application.decision_type.missingness` | **PASS** | 64.81% null |
| `fact_application.doc_completeness_score.missingness` | **PASS** | 56.57% null  (stage-conditional: computed from the uploaded set at submission; null unless submitted) |
| `fact_application.doc_completeness_score.range` | **PASS** | all values within [0.0, 1.0] |
| `fact_application.doc_verification_status.domain` | **PASS** | 4 values within the declared domain |
| `fact_application.dropoff_reason.domain` | **PASS** | 17 values within the declared domain |
| `fact_application.dropoff_reason.missingness` | **PASS** | 12.10% null |
| `fact_application.dropoff_stage.domain` | **PASS** | 6 values within the declared domain |
| `fact_application.dropoff_stage.missingness` | **PASS** | 12.10% null |
| `fact_application.enrolled_flag.binary` | **PASS** | values in {0, 1} |
| `fact_application.enrolled_given_admitted_flag.binary` | **PASS** | values in {0, 1} |
| `fact_application.enrolled_given_admitted_flag.missingness` | **PASS** | 83.12% null |
| `fact_application.enrolled_ts.missingness` | **PASS** | 87.90% null |
| `fact_application.intake_round.range` | **PASS** | all values within [1.0, 2.0] |
| `fact_application.month_of_submission.missingness` | **PASS** | 56.57% null  (stage-conditional: null unless the application was submitted) |
| `fact_application.no_full_row_duplicates` | **PASS** | no duplicated rows |
| `fact_application.offer_deadline.missingness` | **PASS** | 83.12% null |
| `fact_application.pre_sub_active_days.missingness` | **PASS** | 56.57% null  (stage-conditional: engagement summary; null unless the application was submitted) |
| `fact_application.pre_sub_active_days.nonneg` | **PASS** | no negative counts |
| `fact_application.pre_sub_doc_uploads.missingness` | **PASS** | 56.57% null  (stage-conditional: engagement summary; null unless the application was submitted) |
| `fact_application.pre_sub_doc_uploads.nonneg` | **PASS** | no negative counts |
| `fact_application.pre_sub_form_fields_completed.missingness` | **PASS** | 56.57% null  (stage-conditional: engagement summary; null unless the application was submitted) |
| `fact_application.pre_sub_form_fields_completed.nonneg` | **PASS** | no negative counts |
| `fact_application.pre_sub_return_visits.missingness` | **PASS** | 56.57% null  (stage-conditional: engagement summary; null unless the application was submitted) |
| `fact_application.pre_sub_return_visits.nonneg` | **PASS** | no negative counts |
| `fact_application.pre_sub_session_count.missingness` | **PASS** | 56.57% null  (stage-conditional: engagement summary; null unless the application was submitted) |
| `fact_application.pre_sub_session_count.nonneg` | **PASS** | no negative counts |
| `fact_application.pre_sub_session_count.nonneg` | **PASS** | no negative counts |
| `fact_application.pre_sub_total_minutes.missingness` | **PASS** | 56.57% null  (stage-conditional: engagement summary; null unless the application was submitted) |
| `fact_application.pre_sub_total_minutes.nonneg` | **PASS** | no negative counts |
| `fact_application.prediction_stage.domain` | **PASS** | 1 values within the declared domain |
| `fact_application.prediction_stage.missingness` | **PASS** | 56.57% null  (stage-conditional: the stage at the prediction point; null unless submitted) |
| `fact_application.prediction_ts.missingness` | **PASS** | 56.57% null  (stage-conditional: the prediction point; null unless the application was submitted) |
| `fact_application.selection_score.missingness` | **PASS** | 64.81% null |
| `fact_application.selection_score.range` | **PASS** | all values within [0.0, 100.0] |
| `fact_application.split_hint.domain` | **PASS** | 3 values within the declared domain |
| `fact_application.stage_reached.domain` | **PASS** | 7 values within the declared domain |
| `fact_application.touchpoints_count.range` | **PASS** | all values within [1.0, 12.0] |
| `fact_application.week_of_cycle_at_submission.missingness` | **PASS** | 56.57% null  (stage-conditional: null unless the application was submitted) |
| `fact_application.withdrawn_date.missingness` | **PASS** | 99.40% null |
| `fact_engagement.days_before_submission.missingness` | **PASS** | 27.33% null |
| `fact_engagement.device_type.domain` | **PASS** | 3 values within the declared domain |
| `fact_engagement.no_full_row_duplicates` | **PASS** | no duplicated rows |
| `fact_forecast_panel.cum_admit_rate.missingness` | **PASS** | 59.01% null |
| `fact_forecast_panel.cum_enrolment_yield.missingness` | **PASS** | 9.30% null |
| `fact_forecast_panel.cum_submit_to_verify_rate.missingness` | **PASS** | 9.30% null |
| `fact_forecast_panel.no_full_row_duplicates` | **PASS** | no duplicated rows |
| `fact_forecast_panel.split_hint.domain` | **PASS** | 3 values within the declared domain |
| `fact_funnel_event.days_since_prev_stage.missingness` | **PASS** | 33.18% null |
| `fact_funnel_event.no_full_row_duplicates` | **PASS** | no duplicated rows |
| `fact_funnel_event.stage_code.domain` | **PASS** | 7 values within the declared domain |
| `modelling_view.columns` | **PASS** | all 58 declared columns present |
| `modelling_view.pk_unique` | **PASS** | 12,161 rows, application_id unique |

---

## FUNNEL

_33 checks — 0 fail, 0 warn_


| Check | Status | Detail |
|---|---|---|
| `F1.no_duplicate_milestones` | **PASS** | at most one milestone row per (application, stage) |
| `F1.prefix_closed_staircase` | **PASS** | all 28,000 applications have a gap-free stage ladder |
| `F2.strictly_increasing_events` | **PASS** | event timestamps strictly increase along the ladder for every application |
| `F3.every_application_has_events` | **PASS** | all 28,000 applications have a `prospect` event |
| `F3.single_terminal_stage` | **PASS** | every application has exactly one terminal milestone |
| `F5.dropoff_reason_domain` | **PASS** | drop-off reasons are within the declared list |
| `F5.dropoff_reason_present` | **PASS** | every non-enrolled application has a drop-off reason |
| `F5.dropoff_stage_equals_stage_reached` | **PASS** | dropoff_stage == stage_reached for all non-enrolled applications |
| `F5.dropoff_stage_present` | **PASS** | every non-enrolled application has a drop-off stage |
| `F5.enrolled_has_no_dropoff` | **PASS** | enrolled applications carry no drop-off |
| `no_transition.admit_has_admitted_ts` | **PASS** | decision_type = 'admit' implies a recorded admitted_ts |
| `no_transition.admitted_has_decision_ts` | **PASS** | every admitted application has a decision timestamp |
| `no_transition.admitted_requires_admit_decision` | **PASS** | every admitted application has decision_type = 'admit' |
| `no_transition.conditional_target_scope` | **PASS** | enrolled_given_admitted_flag is null unless admitted_flag = 1 |
| `no_transition.enrolled_implies_admitted` | **PASS** | enrolled_flag = 1 implies admitted_flag = 1 |
| `no_transition.enrolled_is_terminal` | **PASS** | enrolled_flag = 1 only at the final stage |
| `no_transition.offer_letter_consistency` | **PASS** | offer_letter_issued == (decision_type == 'admit') |
| `no_transition.scholarship_consistency` | **PASS** | a positive scholarship amount only occurs with scholarship_offered = True |
| `no_transition.verified_has_timestamp` | **PASS** | reaching verification implies a verification timestamp |
| `no_transition.withdrawn_has_no_decision` | **PASS** | withdrawn applications never receive a decision |
| `nulls.stage_conditional[academic_score_pct]` | **PASS** | 12,161 non-null values = the 12,161 applications that reached `application_submitted` |
| `nulls.stage_conditional[application_started_ts]` | **PASS** | 16,230 non-null values = the 16,230 applications that reached `application_started` |
| `nulls.stage_conditional[application_submitted_ts]` | **PASS** | 12,161 non-null values = the 12,161 applications that reached `application_submitted` |
| `nulls.stage_conditional[days_inquiry_to_start]` | **PASS** | 16,230 non-null values = the 16,230 applications that reached `application_started` |
| `nulls.stage_conditional[pre_sub_session_count]` | **PASS** | 12,161 non-null values = the 12,161 applications that reached `application_submitted` |
| `nulls.stage_conditional[prediction_ts]` | **PASS** | 12,161 non-null values = the 12,161 applications that reached `application_submitted` |
| `panel.counts_non_increasing_down_ladder` | **PASS** | cumulative counts never decrease down the funnel ladder |
| `panel.cumulative_ge_weekly[wk_admitted]` | **PASS** | cum_admitted >= wk_admitted in every panel cell |
| `panel.cumulative_ge_weekly[wk_applications_submitted]` | **PASS** | cum_applications_submitted >= wk_applications_submitted in every panel cell |
| `panel.cumulative_ge_weekly[wk_enrolled]` | **PASS** | cum_enrolled >= wk_enrolled in every panel cell |
| `panel.n_applications_matches_opened` | **PASS** | panel.n_applications is the programme-cycle total and equals the final cum_applications_opened |
| `stage_reached_consistency` | **PASS** | fact_application.stage_reached == highest stage in fact_funnel_event |
| `stage_reached_order_consistency` | **PASS** | stage_reached_order matches the stage ladder index |

---

## TEMPORAL

_38 checks — 0 fail, 0 warn_


| Check | Status | Detail |
|---|---|---|
| `cycle_calendar.cycle_end_date_ordered` | **PASS** | cycle calendar is chronologically consistent |
| `cycle_calendar.cycle_start_date_ordered` | **PASS** | cycle calendar is chronologically consistent |
| `cycle_calendar.intake1_application_close_ordered` | **PASS** | cycle calendar is chronologically consistent |
| `cycle_calendar.intake1_application_open_ordered` | **PASS** | cycle calendar is chronologically consistent |
| `cycle_calendar.intake1_decision_end_ordered` | **PASS** | cycle calendar is chronologically consistent |
| `cycle_calendar.intake1_decision_start_ordered` | **PASS** | cycle calendar is chronologically consistent |
| `cycle_calendar.intake1_enrolment_end_ordered` | **PASS** | cycle calendar is chronologically consistent |
| `cycle_calendar.intake1_offer_deadline_ordered` | **PASS** | cycle calendar is chronologically consistent |
| `cycle_calendar.intake2_application_close_ordered` | **PASS** | cycle calendar is chronologically consistent |
| `cycle_calendar.intake2_application_open_ordered` | **PASS** | cycle calendar is chronologically consistent |
| `cycle_calendar.intake2_decision_end_ordered` | **PASS** | cycle calendar is chronologically consistent |
| `cycle_calendar.intake2_decision_start_ordered` | **PASS** | cycle calendar is chronologically consistent |
| `cycle_calendar.intake2_enrolment_end_ordered` | **PASS** | cycle calendar is chronologically consistent |
| `cycle_calendar.intake2_offer_deadline_ordered` | **PASS** | cycle calendar is chronologically consistent |
| `cycle_calendar.monotonic_acyclic` | **PASS** | cycle start dates strictly increase |
| `cycle_calendar.verification_end_date_ordered` | **PASS** | cycle calendar is chronologically consistent |
| `engagement.days_before_submission_nonneg` | **PASS** | days_before_submission is never negative |
| `engagement.never_after_prediction_point` | **PASS** | all 27,882 engagement rows for submitted applications are on or before the prediction date |
| `engagement.only_for_started_applications` | **PASS** | engagement exists only for applications that reached application_started |
| `enrolment.before_offer_deadline` | **PASS** | no enrolment occurs after the offer deadline |
| `enrolment.within_round_window` | **PASS** | every enrolment is inside its intake round's registration window |
| `events.inside_cycle_window` | **PASS** | all 84,383 funnel events fall inside their cycle window |
| `forecast_horizon_1w_supported` | **PASS** | H = 1w: the origin+H week exists for all 552 eligible forecast origins |
| `forecast_horizon_2w_supported` | **PASS** | H = 2w: the origin+H week exists for all 552 eligible forecast origins |
| `forecast_horizon_4w_supported` | **PASS** | H = 4w: the origin+H week exists for all 552 eligible forecast origins |
| `forecast_horizon_6w_supported` | **PASS** | H = 6w: the origin+H week exists for all 552 eligible forecast origins |
| `forecast_origins_available` | **PASS** | 552 eligible forecast origins across programme x cycle x week |
| `inquiry.within_cycle_window` | **PASS** | every inquiry is on or after the cycle application open date |
| `panel.complete_grid` | **PASS** | 2,064 panel cells = programmes x cycles x weeks |
| `panel.week_index_bounded` | **PASS** | the last panel week of every programme-cycle is week index total_weeks - 1 |
| `panel.weeks_are_seven_days` | **PASS** | every panel week spans 7 days |
| `panel.weeks_start_on_monday` | **PASS** | every panel week starts on a Monday |
| `split.chronological` | **PASS** | split_hint is a pure function of cycle_id (train / validation / test are consecutive, non-overlapping cycle ranges) |
| `split.matches_contract` | **PASS** | every cycle carries the split_hint assigned to it by the documented chronological rule (cycles are ordered by cycle_start_date) |
| `submission.within_round_close` | **PASS** | every submission is on or before its intake round close date |
| `temporal_coverage` | **PASS** | 2022-06-10 .. 2026-02-26 (44 months across 4 closed cycles) |
| `verification.before_round_decision_window` | **PASS** | every verification completes before its own intake round's decision window opens |
| `withdrawal.precedes_decision` | **PASS** | withdrawn applications have no decision timestamp |

---

## ML

_104 checks — 0 fail, 0 warn_


| Check | Status | Detail |
|---|---|---|
| `feature.degenerate_binary` | **PASS** | 58 columns, 28 numeric, 10 with <=2 levels |
| `feature.variation` | **PASS** | every modelling-view column varies |
| `feature_set.available[decision]` | **PASS** | 43/45 declared `decision` features present in the modelling view |
| `feature_set.available[primary]` | **PASS** | 43/45 declared `primary` features present in the modelling view |
| `leakage.boundary[decision].academic_score_band` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].academic_score_pct` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].acquisition_channel` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].acquisition_source` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].annual_fee_inr` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].application_started_ts` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].application_submitted_ts` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].base_seat_capacity` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].campaign_id` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].campus_region_id` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].cohort_label` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].cycle_id` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].days_inquiry_to_start` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].days_inquiry_to_submit` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].days_start_to_submit` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].days_to_round_close_at_start` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].demand_weight` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].doc_completeness_score` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].duration_years` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].education_level` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].fee_scholarship_applied` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].first_touch_date` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].gender_band` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].inquiry_ts` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].intake_round` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].is_multi_touch` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].is_referral_alumni` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].is_repeat_applicant_at_prediction` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].mean_distance_km_to_campus` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].month_of_submission` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].pre_sub_active_days` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].pre_sub_doc_uploads` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].pre_sub_form_fields_completed` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].pre_sub_return_visits` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].pre_sub_session_count` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].pre_sub_total_minutes` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].programme_id` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].region_id` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].review_duration_days` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].selectivity_tier` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].split_hint` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].touchpoints_count` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[decision].week_of_cycle_at_submission` | **PASS** | `admission_decision_ts` <= `admission_decision_ts` on every row |
| `leakage.boundary[primary].academic_score_band` | **PASS** | `application_submitted_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].academic_score_pct` | **PASS** | `application_submitted_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].acquisition_channel` | **PASS** | `first_touch_date` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].acquisition_source` | **PASS** | `first_touch_date` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].annual_fee_inr` | **PASS** | `inquiry_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].application_started_ts` | **PASS** | `application_started_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].application_submitted_ts` | **PASS** | `application_submitted_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].base_seat_capacity` | **PASS** | `inquiry_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].campaign_id` | **PASS** | `first_touch_date` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].campus_region_id` | **PASS** | `inquiry_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].cohort_label` | **PASS** | `inquiry_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].cycle_id` | **PASS** | `inquiry_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].days_inquiry_to_start` | **PASS** | `application_started_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].days_inquiry_to_submit` | **PASS** | `application_submitted_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].days_start_to_submit` | **PASS** | `application_submitted_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].days_to_round_close_at_start` | **PASS** | `application_started_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].demand_weight` | **PASS** | `inquiry_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].doc_completeness_score` | **PASS** | `application_submitted_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].duration_years` | **PASS** | `inquiry_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].education_level` | **PASS** | `inquiry_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].fee_scholarship_applied` | **PASS** | `application_submitted_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].first_touch_date` | **PASS** | `first_touch_date` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].gender_band` | **PASS** | `inquiry_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].inquiry_ts` | **PASS** | `inquiry_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].intake_round` | **PASS** | `inquiry_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].is_multi_touch` | **PASS** | `first_touch_date` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].is_referral_alumni` | **PASS** | `first_touch_date` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].is_repeat_applicant_at_prediction` | **PASS** | `application_submitted_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].mean_distance_km_to_campus` | **PASS** | `inquiry_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].month_of_submission` | **PASS** | `application_submitted_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].pre_sub_active_days` | **PASS** | `application_submitted_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].pre_sub_doc_uploads` | **PASS** | `application_submitted_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].pre_sub_form_fields_completed` | **PASS** | `application_submitted_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].pre_sub_return_visits` | **PASS** | `application_submitted_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].pre_sub_session_count` | **PASS** | `application_submitted_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].pre_sub_total_minutes` | **PASS** | `application_submitted_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].programme_id` | **PASS** | `inquiry_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].region_id` | **PASS** | `inquiry_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].review_duration_days` | **PASS** | `inquiry_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].selectivity_tier` | **PASS** | `inquiry_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].split_hint` | **PASS** | `inquiry_ts` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].touchpoints_count` | **PASS** | `first_touch_date` <= `application_submitted_ts` on every row |
| `leakage.boundary[primary].week_of_cycle_at_submission` | **PASS** | `application_submitted_ts` <= `application_submitted_ts` on every row |
| `leakage.modelling_view_primary_clean` | **PASS** | the denormalised modelling view exposes no POST_OUTCOME field as a primary feature |
| `leakage.no_post_outcome_in_decision_features` | **PASS** | none of the 45 `decision` features is POST_OUTCOME or TARGET |
| `leakage.no_post_outcome_in_primary_features` | **PASS** | none of the 45 `primary` features is POST_OUTCOME or TARGET |
| `leakage.no_target_duplicates` | **PASS** | no feature duplicates the target |
| `leakage.selection_score_excluded` | **PASS** | the deliberate leakage trap `selection_score` is absent from the modelling view |
| `leakage.traps_are_dangerous` | **PASS** | post-outcome columns (deliberate leakage traps) rank against the target as: `doc_verification_status`=0.622, `days_submitted_to_verified`=0.565, `doc_query_raised`=0.556, `doc_query_count`=0.548, `region_type`=0.505. They are excluded from every feature set by construction. |
| `secondary_target.balance` | **PASS** | enrolled_given_admitted_flag mean = 0.7167 over 4,727 admits |
| `split.content[test]` | **PASS** | 3,001 rows (24.7%), enrolled rate 0.2629 |
| `split.content[train]` | **PASS** | 6,154 rows (50.6%), enrolled rate 0.2923 |
| `split.content[validation]` | **PASS** | 3,006 rows (24.7%), enrolled rate 0.2661 |
| `target.balance` | **PASS** | enrolled_flag mean = 0.2786 (3,388 positives / 12,161 rows) |
| `target.not_trivially_predictable` | **PASS** | strongest single-feature rank AUC vs enrolled_flag among the 41 safe primary features: `doc_completeness_score`=0.713, `academic_score_pct`=0.706, `academic_score_band`=0.628, `annual_fee_inr`=0.627, `programme_id`=0.618, `campus_region_id`=0.597, `demand_weight`=0.592, `review_duration_days`=0.587 |
| `target.volume` | **PASS** | modelling view has 12,161 rows, raw fact has 28,000 application rows |
| `tertiary_target.balance` | **PASS** | admitted_flag mean = 0.3887 over 12,161 rows |

---

## REALISM

_16 checks — 0 fail, 0 warn_


| Check | Status | Detail |
|---|---|---|
| `behaviour.engagement_depth` | **PASS** | 38,369 engagement rows = 2.36 activity days per started application |
| `behaviour.withdrawal_rate` | **PASS** | 0.604% of applications withdrawn after submission |
| `distribution.acquisition_channel` | **PASS** | channel shares: direct=0.096, education_fair=0.090, email_campaign=0.106, organic_search=0.199, paid_search=0.177, partner_agency=0.090, referral=0.106, social_media=0.135 |
| `distribution.cycle` | **PASS** | cycle shares: CYC-2022=0.251, CYC-2023=0.249, CYC-2024=0.253, CYC-2025=0.247 |
| `distribution.intake_round` | **PASS** | intake 1 = 0.424, intake 2 = 0.576 |
| `distribution.programme` | **PASS** | 12 programmes, share range 0.031 - 0.158 |
| `distribution.region` | **PASS** | 8 regions, share range 0.051 - 0.239 |
| `funnel.conversion_rates` | **PASS** | step conversions: prospect->application_started: 0.580 (top-of-funnel 0.580) \| application_started->application_submitted: 0.749 (top-of-funnel 0.434) \| application_submitted->application_verified: 0.824 (top-of-funnel 0.358) \| application_verified->admission_decision: 0.983 (top-of-funnel 0.352) \| admission_decision->admitted: 0.480 (top-of-funnel 0.169) \| admitted->enrolled: 0.717 (top-of-funnel 0.121) |
| `funnel.no_zero_volume_stage` | **PASS** | every funnel stage is populated: prospect=28,000, application_started=16,230, application_submitted=12,161, application_verified=10,023, admission_decision=9,854, admitted=4,727, enrolled=3,388 |
| `panel.reconciles_submissions` | **PASS** | final cumulative panel submitted counts reconcile exactly with fact_application |
| `panel.reconciles_with_fact` | **PASS** | final cumulative panel enrolled counts reconcile exactly with fact_application |
| `segment.channel_all_populated` | **PASS** | channel volumes: direct=2,674, education_fair=2,533, email_campaign=2,980, organic_search=5,562, paid_search=4,966, partner_agency=2,513, referral=2,981, social_media=3,791 |
| `segment.channel_variation` | **PASS** | enrolment yield by first-touch channel ranges 0.092 - 0.150 (sd 0.018). ASSOCIATION ONLY - channel mix confounds this. |
| `segment.cycle_variation` | **PASS** | enrolment yield by cycle: CYC-2022=0.133, CYC-2023=0.124, CYC-2024=0.113, CYC-2025=0.114 |
| `segment.demand_crowding_effect` | **PASS** | corr(programme demand, admit rate) = -0.175 (expected negative: crowding tightens selectivity) |
| `segment.programme_variation` | **PASS** | enrolment yield across programmes ranges 0.066 - 0.184 (sd 0.045); admit rate 0.294 - 0.706 |

---

> The primary project dataset is synthetic and was generated according to the documented AdmitFlow admission-funnel specification for development, experimentation, evaluation, and demonstration. It does not represent any real institution, applicant, or admission outcome.

>
> Any metric computed on this dataset is a property of the documented generator assumptions. It must never be reported as real-world institutional performance.

