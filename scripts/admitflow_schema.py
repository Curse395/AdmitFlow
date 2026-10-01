"""
ADMITFLOW - canonical schema and column registry.

This module is the SINGLE SOURCE OF TRUTH for:
  * every entity and every column of the AdmitFlow synthetic dataset
  * field classification (KEY / REFERENCE / GENERATED / DERIVED / TARGET / POST_OUTCOME)
  * prediction-time availability
  * leakage risk
  * feature-set membership (allow-lists for the `primary` and `decision` tasks)
  * the source timestamp a feature's content depends on

It is imported by generate_dataset.py, validate_dataset.py and profile_dataset.py so that a
column cannot exist without being documented, classified and validated, and so that
docs/data_dictionary.md is rendered from the same definitions the data is built from.

SYNTHETIC DATA NOTICE
---------------------
The primary project dataset is synthetic and was generated according to the documented AdmitFlow
admission-funnel specification for development, experimentation, evaluation, and demonstration.
It does not represent any real institution, applicant, or admission outcome.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------------------
# Fictionality
# --------------------------------------------------------------------------------------

FICTIONALITY_STATEMENT = (
    "The primary project dataset is synthetic and was generated according to the documented "
    "AdmitFlow admission-funnel specification for development, experimentation, evaluation, and "
    "demonstration. It does not represent any real institution, applicant, or admission outcome."
)

PERFORMANCE_DISCLAIMER = (
    "Any metric computed on this dataset is a property of the documented generator assumptions. "
    "It must never be reported as real-world institutional performance."
)

# --------------------------------------------------------------------------------------
# Roles / availability / feature sets
# --------------------------------------------------------------------------------------

ROLE_KEY = "KEY"                # primary key or foreign key
ROLE_REFERENCE = "REFERENCE"    # reference-data attribute of a dimension table
ROLE_GENERATED = "GENERATED"    # drawn by the generator from its stated mechanism
ROLE_DERIVED = "DERIVED"        # computed from other columns of this dataset
ROLE_TARGET = "TARGET"          # a supervised prediction target
ROLE_POST_OUTCOME = "POST_OUTCOME"  # known only after the prediction point -> never a feature

ROLE_ORDER = [ROLE_KEY, ROLE_REFERENCE, ROLE_GENERATED, ROLE_DERIVED, ROLE_TARGET,
              ROLE_POST_OUTCOME]

AVAIL_NA = "not_applicable"
AVAIL_PRE = "pre_submission"        # strictly before application_submitted_ts
AVAIL_AT = "at_prediction_point"    # known at / by the prediction point, not after
AVAIL_POST = "post_prediction_point"

AVAILABILITY_LEGEND = {
    AVAIL_PRE: "Content is fully determined strictly before `application_submitted_ts`.",
    AVAIL_AT: "Content is determined at or before `application_submitted_ts` and does not change "
              "afterwards.",
    AVAIL_POST: "Content is determined after `application_submitted_ts`. FORBIDDEN as a feature "
                "of the primary target.",
    AVAIL_NA: "Key, target, or reference attribute; not a predictive feature.",
}

FEATURE_SET_PRIMARY = "primary"
FEATURE_SET_DECISION = "decision"
FEATURE_SETS = (FEATURE_SET_PRIMARY, FEATURE_SET_DECISION)

LEAK_NONE = "none"
LEAK_LOW = "low"
LEAK_HIGH = "high"

LEAKAGE_LEGEND = {
    LEAK_NONE: "Safe. No content dated after the prediction point.",
    LEAK_LOW: "Safe but indirectly sensitive: a dimension attribute correlated with a protected "
              "attribute (region, gender) or with programme capacity. Usable; interpret with care.",
    LEAK_HIGH: "Unsafe. Content is dated after the prediction point. Using it as a feature "
               "invalidates the evaluation.",
}

DTYPES = ("str", "int64", "float64", "bool", "date", "timestamp")

SPLIT_LABELS = ("train", "validation", "test")


def split_hint(cycle_index: int, n_cycles: int) -> str:
    """Chronological train/validation/test assignment for cycle ``cycle_index`` (0-based).

    Single source of truth: both the generator and the validator call this, so a
    mismatch between produced and expected ``split_hint`` values is a real defect.
    """
    if n_cycles <= 2:
        return SPLIT_LABELS[0] if cycle_index == 0 else SPLIT_LABELS[2]
    if n_cycles == 3:
        return SPLIT_LABELS[cycle_index]
    frac = cycle_index / (n_cycles - 1)
    if frac < 0.5:
        return SPLIT_LABELS[0]
    if frac < 0.75:
        return SPLIT_LABELS[1]
    return SPLIT_LABELS[2]


# --------------------------------------------------------------------------------------
# Funnel
# --------------------------------------------------------------------------------------

FUNNEL_STAGES: Tuple[dict, ...] = (
    {
        "stage_order": 1,
        "stage_code": "prospect",
        "stage_name": "Prospect / inquiry",
        "stage_kind": "CUMULATIVE_MILESTONE",
        "allows_reentry": 0,
        "requires_all_prior_stages": 1,
        "description": "Lead record raised against a programme and admission cycle by marketing, "
                       "walk-in, partner or self-initiated enquiry.",
    },
    {
        "stage_order": 2,
        "stage_code": "application_started",
        "stage_name": "Application started",
        "stage_kind": "CUMULATIVE_MILESTONE",
        "allows_reentry": 0,
        "requires_all_prior_stages": 1,
        "description": "Applicant opened the online application form. Re-opening the form is an "
                       "engagement day, not a second milestone; the milestone timestamp is the "
                       "first session.",
    },
    {
        "stage_order": 3,
        "stage_code": "application_submitted",
        "stage_name": "Application submitted",
        "stage_kind": "CUMULATIVE_MILESTONE",
        "allows_reentry": 0,
        "requires_all_prior_stages": 1,
        "description": "Application payload submitted on or before the intake round close date. "
                       "This is the prediction point of the primary task.",
    },
    {
        "stage_order": 4,
        "stage_code": "application_verified",
        "stage_name": "Application verified",
        "stage_kind": "CUMULATIVE_MILESTONE",
        "allows_reentry": 0,
        "requires_all_prior_stages": 1,
        "description": "Documents received and checked as complete and eligibility-checked. May "
                       "contain an internal doc-query loop before the milestone is granted.",
    },
    {
        "stage_order": 5,
        "stage_code": "admission_decision",
        "stage_name": "Decision released",
        "stage_kind": "CUMULATIVE_MILESTONE",
        "allows_reentry": 0,
        "requires_all_prior_stages": 1,
        "description": "A formal dated decision (admit or reject) released to the applicant. "
                       "One decision per application, ever.",
    },
    {
        "stage_order": 6,
        "stage_code": "admitted",
        "stage_name": "Admitted",
        "stage_kind": "CUMULATIVE_MILESTONE",
        "allows_reentry": 0,
        "requires_all_prior_stages": 1,
        "description": "Seat allotted and offer conditions cleared. Reached only by admits.",
    },
    {
        "stage_order": 7,
        "stage_code": "enrolled",
        "stage_name": "Enrolled",
        "stage_kind": "CUMULATIVE_MILESTONE",
        "allows_reentry": 0,
        "requires_all_prior_stages": 1,
        "description": "Registration completed and first instalment recorded. Primary target "
                       "milestone.",
    },
)

STAGE_CODES: Tuple[str, ...] = tuple(s["stage_code"] for s in FUNNEL_STAGES)
STAGE_ORDER: Dict[str, int] = {s["stage_code"]: s["stage_order"] for s in FUNNEL_STAGES}

DROP_REASONS: Tuple[str, ...] = (
    # dropped at prospect
    "no_response",
    "browsed_only",
    "enquiry_closed_unqualified",
    # dropped at application_started
    "form_abandoned",
    "deadline_missed",
    "requirements_unclear",
    # dropped at application_submitted
    "incomplete_documents",
    "ineligible_qualification",
    "verification_timeout",
    # dropped at application_verified
    "withdrawn_by_applicant",
    "accepted_elsewhere_withdrawn",
    # dropped at admission_decision
    "below_merit_cutoff",
    "eligibility_criteria_failed",
    "capacity_exhausted",
    # dropped at admitted
    "offer_not_accepted",
    "chose_other_institution",
    "financial_constraint",
    "offer_deadline_lapsed",
)

ACQUISITION_CHANNELS: Tuple[str, ...] = (
    "organic_search",
    "paid_search",
    "social_media",
    "email_campaign",
    "referral",
    "direct",
    "education_fair",
    "partner_agency",
)

CAMPAIGN_CHANNELS: Tuple[str, ...] = (
    "paid_search",
    "social_media",
    "email_campaign",
    "partner_agency",
)

GENDER_BANDS: Tuple[str, ...] = ("female", "male", "other_or_prefer_not_to_say")
EDUCATION_LEVELS: Tuple[str, ...] = ("higher_secondary", "diploma", "undergraduate", "other")
REGION_TYPES: Tuple[str, ...] = ("metro", "tier2", "tier3", "rural_remote")
SELECTIVITY_TIERS: Tuple[str, ...] = ("emerging", "medium", "high")
DECISION_TYPES: Tuple[str, ...] = ("admit", "reject")
DOC_VERIFICATION_STATUSES: Tuple[str, ...] = (
    "verified", "returned_for_correction", "rejected_ineligible", "not_initiated")
DEVICE_TYPES: Tuple[str, ...] = ("mobile", "desktop", "tablet")
ACADEMIC_SCORE_BANDS: Tuple[str, ...] = ("lt_60", "60_69", "70_79", "80_89", "90_plus")
SPLIT_HINTS: Tuple[str, ...] = ("train", "validation", "test")

ACQUISITION_SOURCE_EXAMPLES: Dict[str, Tuple[str, ...]] = {
    "organic_search": ("google_organic", "bing_organic", "programme_page", "content_blog"),
    "paid_search": ("google_ads_brand", "google_ads_generic", "meta_ads_prospect"),
    "social_media": ("instagram_organic", "linkedin_organic", "youtube_organic", "meta_ads_retarget"),
    "email_campaign": ("newsletter_prospectus", "alumni_referral_mail", "open_day_invite"),
    "referral": ("alumni_referral", "parent_referral", "school_counsellor", "peer_referral"),
    "direct": ("direct_web", "app_download", "walk_in"),
    "education_fair": ("school_fair", "district_career_fair", "college_career_fair"),
    "partner_agency": ("overseas_counsellor", "education_consultant", "nri_helpdesk"),
}

# --------------------------------------------------------------------------------------
# Registry primitives
# --------------------------------------------------------------------------------------

# Columns whose value only exists once the application has reached a particular funnel
# stage. They are declared `required=True` (they belong to the entity) but `nullable=True`,
# because for an application that left the funnel earlier they are structurally null.
# The null pattern is informative, not a defect: "no submission timestamp" IS the fact that
# the applicant never submitted. The validation report checks the null RATE against the
# stage distribution rather than requiring zero nulls.
STAGE_CONDITIONAL_COLUMNS: Dict[str, str] = {
    "application_started_ts": "null unless the application reached `application_started`",
    "application_submitted_ts": "null unless the application reached `application_submitted`",
    "prediction_ts": "the prediction point; null unless the application was submitted",
    "prediction_stage": "the stage at the prediction point; null unless submitted",
    "academic_score_pct": "declared on the form at submission; null unless submitted",
    "academic_score_band": "banded from `academic_score_pct`; null unless submitted",
    "doc_completeness_score": "computed from the uploaded set at submission; null unless submitted",
    "days_inquiry_to_start": "null unless the application reached `application_started`",
    "days_start_to_submit": "null unless the application was submitted",
    "days_inquiry_to_submit": "null unless the application was submitted",
    "days_to_round_close_at_start": "null unless the application reached `application_started`",
    "week_of_cycle_at_submission": "null unless the application was submitted",
    "month_of_submission": "null unless the application was submitted",
    "pre_sub_session_count": "engagement summary; null unless the application was submitted",
    "pre_sub_active_days": "engagement summary; null unless the application was submitted",
    "pre_sub_total_minutes": "engagement summary; null unless the application was submitted",
    "pre_sub_doc_uploads": "engagement summary; null unless the application was submitted",
    "pre_sub_form_fields_completed": "engagement summary; null unless the application was submitted",
    "pre_sub_return_visits": "engagement summary; null unless the application was submitted",
}

NULLABILITY_NOTE = (
    "Nullability is declared per column. A column may be `required` (it belongs to the "
    "entity and is always written) yet `nullable` (its value only exists for the subset of "
    "rows that reached a given funnel stage). See `STAGE_CONDITIONAL_COLUMNS` in "
    "`scripts/admitflow_schema.py` for the population of each such column."
)


@dataclass(frozen=True)
class Column:
    name: str
    dtype: str
    role: str
    description: str
    generation_logic: str
    example: str = ""
    required: bool = True
    availability: str = AVAIL_NA
    leakage: str = LEAK_NONE
    feature_sets: Tuple[str, ...] = ()
    categories: Optional[Tuple[str, ...]] = None
    source_ts_field: Optional[str] = None      # column holding the source moment of this feature
    source_ts_field_decision: Optional[str] = None
    secondary_target: bool = False
    fk: Optional[str] = None                  # "entity.column"
    nullable: bool = False

    @property
    def is_feature(self) -> bool:
        return bool(self.feature_sets)


@dataclass(frozen=True)
class Entity:
    name: str
    grain: str
    primary_key: str
    description: str
    columns: Tuple[Column, ...]
    role_in_pipeline: str = ""

    @property
    def column_names(self) -> Tuple[str, ...]:
        return tuple(c.name for c in self.columns)

    def col(self, name: str) -> Column:
        for c in self.columns:
            if c.name == name:
                return c
        raise KeyError(f"{self.name}.{name} not found in schema registry")


@dataclass(frozen=True)
class MVColumn:
    """A column of the denormalised primary modelling view (data/processed)."""
    name: str
    source_entity: str
    source_column: str
    description: str
    role: str
    availability: str
    leakage: str
    in_primary: bool
    in_decision: bool
    fk: Optional[str] = None


def _c(*args, **kwargs) -> Column:
    kwargs = dict(kwargs)
    if "nullable" not in kwargs and args[0] in STAGE_CONDITIONAL_COLUMNS:
        # stage-conditional columns are always written but only carry a value for the rows
        # that reached the relevant stage; see STAGE_CONDITIONAL_COLUMNS.
        kwargs["nullable"] = True
    col = Column(*args, **kwargs)
    if col.dtype not in DTYPES:
        raise ValueError(f"bad dtype {col.dtype} for {col.name}")
    if col.role not in ROLE_ORDER:
        raise ValueError(f"bad role {col.role} for {col.name}")
    return col


# --------------------------------------------------------------------------------------
# dim_funnel_stage
# --------------------------------------------------------------------------------------

dim_funnel_stage = Entity(
    name="dim_funnel_stage",
    grain="one row per admission funnel stage",
    primary_key="stage_code",
    description="Reference ladder of the seven AdmitFlow admission funnel stages, including "
                "re-entry and ordering semantics used by validation.",
    role_in_pipeline="Funnel definition / analytics reference",
    columns=(
        _c("stage_order", "int64", ROLE_REFERENCE,
           "Integer position of the stage in the ladder (1..7).",
           "Fixed constant ladder declared in the analytical contract.", "1", availability=AVAIL_NA),
        _c("stage_code", "str", ROLE_KEY,
           "Stable machine key of the stage.",
           "Fixed constant declared in the analytical contract.", "application_submitted",
           availability=AVAIL_NA, categories=STAGE_CODES),
        _c("stage_name", "str", ROLE_REFERENCE,
           "Human readable stage name.",
           "Fixed constant.", "Application submitted", availability=AVAIL_NA),
        _c("stage_kind", "str", ROLE_REFERENCE,
           "Whether the stage is a cumulative milestone or a discrete event.",
           "Fixed constant; all AdmitFlow stages are cumulative milestones.",
           "CUMULATIVE_MILESTONE", availability=AVAIL_NA,
           categories=("CUMULATIVE_MILESTONE", "EVENT")),
        _c("allows_reentry", "bool", ROLE_REFERENCE,
           "Whether the stage can be re-entered after being left.",
           "Fixed constant. Session-level revisits of `application_started` are recorded as "
           "engagement days, not as repeated milestones.",
           "False", availability=AVAIL_NA),
        _c("requires_all_prior_stages", "bool", ROLE_REFERENCE,
           "Whether reaching the stage requires every earlier stage to have been reached.",
           "Fixed constant, True for all stages (prefix-closed funnel, invariant F1).", "True",
           availability=AVAIL_NA),
        _c("stage_description", "str", ROLE_REFERENCE,
           "Full definition, entry condition and exit condition of the stage.",
           "Fixed constant transcribed from the analytical contract.",
           "Application payload submitted on or before the intake round close date.",
           availability=AVAIL_NA),
    ),
)

# --------------------------------------------------------------------------------------
# dim_region
# --------------------------------------------------------------------------------------

dim_region = Entity(
    name="dim_region",
    grain="one row per applicant-origin region",
    primary_key="region_id",
    description="Fictional coarse geography of applicant origin. Deliberately coarse: the dataset "
                "carries no PII and no sub-district detail.",
    role_in_pipeline="Segmentation / cohort analysis dimension",
    columns=(
        _c("region_id", "str", ROLE_KEY, "Region key.", "Fixed constant dimension.", "REG-04",
           availability=AVAIL_NA),
        _c("region_name", "str", ROLE_REFERENCE, "Fictional region name.",
           "Fixed constant dimension.", "Coastal South", availability=AVAIL_NA),
        _c("region_type", "str", ROLE_REFERENCE,
           "Settlement type of the region.", "Fixed constant dimension.", "tier2",
           availability=AVAIL_NA, leakage=LEAK_LOW, categories=REGION_TYPES),
        _c("mean_distance_km_to_campus", "float64", ROLE_GENERATED,
           "Mean travel distance from the region to the institution campus; a proxy for "
           "relocation cost and therefore for offer acceptance.",
           "Fixed constant per region, then perturbed +/-12% per cycle to create mild "
           "year-over-year variation.", "842.5", availability=AVAIL_PRE, leakage=LEAK_LOW,
           feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
           source_ts_field="inquiry_ts", source_ts_field_decision="admission_decision_ts"),
        _c("region_inquiry_weight", "float64", ROLE_GENERATED,
           "Share of prospects originating in the region.",
           "Fixed constant share weights, renormalised across regions; drifts +/-10% per cycle.",
           "0.145", availability=AVAIL_PRE, leakage=LEAK_LOW,
           feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
           source_ts_field="inquiry_ts", source_ts_field_decision="admission_decision_ts"),
    ),
)

# --------------------------------------------------------------------------------------
# dim_programme
# --------------------------------------------------------------------------------------

dim_programme = Entity(
    name="dim_programme",
    grain="one row per programme offered by the fictional institution",
    primary_key="programme_id",
    description="Programme reference data. Contains only PUBLISHED programme attributes; the "
                "latent merit cutoff that actually drives decisions is deliberately withheld.",
    role_in_pipeline="Core analysis dimension for programme comparison and forecasting",
    columns=(
        _c("programme_id", "str", ROLE_KEY, "Programme key.", "Fixed constant dimension.",
           "PGM-07", availability=AVAIL_NA),
        _c("programme_name", "str", ROLE_REFERENCE, "Programme name.",
           "Fixed constant dimension.", "B.Sc. Computer Science", availability=AVAIL_NA),
        _c("programme_code", "str", ROLE_REFERENCE, "Short programme code.",
           "Fixed constant dimension.", "BSC-CS", availability=AVAIL_NA),
        _c("faculty", "str", ROLE_REFERENCE, "Faculty the programme belongs to.",
           "Fixed constant dimension.", "Faculty of Science", availability=AVAIL_NA,
           categories=("Faculty of Science", "Faculty of Commerce", "Faculty of Management",
                       "Faculty of Humanities", "Faculty of Technology")),
        _c("award_level", "str", ROLE_REFERENCE, "Award level of the programme.",
           "Fixed constant dimension, all undergraduate.", "UG", availability=AVAIL_NA,
           categories=("UG",)),
        _c("duration_years", "int64", ROLE_GENERATED,
           "Programme duration in years.", "Fixed constant per programme.", "3",
           availability=AVAIL_PRE, leakage=LEAK_LOW,
           feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
           source_ts_field="inquiry_ts", source_ts_field_decision="admission_decision_ts"),
        _c("annual_fee_inr", "int64", ROLE_GENERATED,
           "Published annual tuition fee in INR; a driver of offer acceptance through the "
           "unobserved financial-constraint factor.",
           "Log-normal draw per programme, rounded to the nearest 500 INR.", "146000",
           availability=AVAIL_PRE, leakage=LEAK_LOW,
           feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
           source_ts_field="inquiry_ts", source_ts_field_decision="admission_decision_ts"),
        _c("base_seat_capacity", "int64", ROLE_GENERATED,
           "Approved intake capacity for one admission cycle.",
           "Fixed constant per programme.", "120", availability=AVAIL_PRE, leakage=LEAK_LOW,
           feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
           source_ts_field="inquiry_ts", source_ts_field_decision="admission_decision_ts"),
        _c("selectivity_tier", "str", ROLE_REFERENCE,
           "Published selectivity band.",
           "Fixed constant per programme.", "high", availability=AVAIL_PRE, leakage=LEAK_LOW,
           feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
           categories=SELECTIVITY_TIERS, source_ts_field="inquiry_ts",
           source_ts_field_decision="admission_decision_ts"),
        _c("review_duration_days", "float64", ROLE_GENERATED,
           "Median days from submission to document verification.",
           "Fixed constant per programme, derived from faculty workload.", "6.4",
           availability=AVAIL_PRE, leakage=LEAK_LOW,
           feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
           source_ts_field="inquiry_ts", source_ts_field_decision="admission_decision_ts"),
        _c("demand_weight", "float64", ROLE_GENERATED,
           "Relative attractiveness driving how many prospects the programme attracts.",
           "Fixed constant per programme, renormalised across programmes; drifts year over year.",
           "0.131", availability=AVAIL_PRE, leakage=LEAK_LOW,
           feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
           source_ts_field="inquiry_ts", source_ts_field_decision="admission_decision_ts"),
        _c("campus_region_id", "str", ROLE_KEY,
           "Region in which the programme is taught.", "Fixed constant dimension.", "REG-01",
           availability=AVAIL_PRE, leakage=LEAK_LOW, fk="dim_region.region_id",
           feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
           source_ts_field="inquiry_ts", source_ts_field_decision="admission_decision_ts"),
    ),
)

# --------------------------------------------------------------------------------------
# dim_admission_cycle
# --------------------------------------------------------------------------------------

dim_admission_cycle = Entity(
    name="dim_admission_cycle",
    grain="one row per admission cycle",
    primary_key="cycle_id",
    description="Calendar and deadline structure of an admission cycle, including both intake "
                "rounds. All four cycles in this dataset are closed and fully finalised.",
    role_in_pipeline="Time dimension, drives chronological splits and forecast origins",
    columns=(
        _c("cycle_id", "str", ROLE_KEY, "Admission cycle key.", "Fixed constant dimension.",
           "CYC-2024", availability=AVAIL_NA),
        _c("academic_year_label", "str", ROLE_REFERENCE,
           "Human readable academic year.", "Derived from the cycle start year.", "AY2024-25",
           availability=AVAIL_NA),
        _c("cycle_start_date", "date", ROLE_DERIVED,
           "First day of the cycle (equal to intake 1 application open date).",
           "Derived: intake 1 application open date.", "2024-06-01", availability=AVAIL_NA),
        _c("cycle_end_date", "date", ROLE_DERIVED,
           "Last day of the cycle (equal to intake 2 enrolment end date).",
           "Derived: intake 2 enrolment end date.", "2025-03-20", availability=AVAIL_NA),
        _c("intake1_application_open", "date", ROLE_REFERENCE,
           "Intake 1 applications open.", "Fixed cycle template.", "2024-06-01",
           availability=AVAIL_NA),
        _c("intake1_application_close", "date", ROLE_REFERENCE,
           "Intake 1 application submission deadline. Determines `intake_round` at prospect time.",
           "Fixed cycle template.", "2024-10-15", availability=AVAIL_NA),
        _c("intake1_decision_start", "date", ROLE_REFERENCE,
           "First day of the intake 1 decision release window.", "Fixed cycle template.",
           "2024-11-20", availability=AVAIL_NA),
        _c("intake1_decision_end", "date", ROLE_REFERENCE,
           "Last day of the intake 1 decision release window.", "Fixed cycle template.",
           "2024-11-27", availability=AVAIL_NA),
        _c("intake1_offer_deadline", "date", ROLE_REFERENCE,
           "Last date on which an intake 1 offer can be accepted.",
           "Fixed cycle template.", "2025-01-10", availability=AVAIL_NA),
        _c("intake1_enrolment_end", "date", ROLE_REFERENCE,
           "Last date of intake 1 registration and fee payment.", "Fixed cycle template.",
           "2025-02-05", availability=AVAIL_NA),
        _c("intake2_application_open", "date", ROLE_REFERENCE,
           "Intake 2 applications open (day after intake 1 close).", "Fixed cycle template.",
           "2024-10-16", availability=AVAIL_NA),
        _c("intake2_application_close", "date", ROLE_REFERENCE,
           "Intake 2 application submission deadline.", "Fixed cycle template.", "2024-12-20",
           availability=AVAIL_NA),
        _c("intake2_decision_start", "date", ROLE_REFERENCE,
           "First day of the intake 2 decision release window.", "Fixed cycle template.",
           "2025-01-15", availability=AVAIL_NA),
        _c("intake2_decision_end", "date", ROLE_REFERENCE,
           "Last day of the intake 2 decision release window.", "Fixed cycle template.",
           "2025-01-22", availability=AVAIL_NA),
        _c("intake2_offer_deadline", "date", ROLE_REFERENCE,
           "Last date on which an intake 2 offer can be accepted.", "Fixed cycle template.",
           "2025-02-25", availability=AVAIL_NA),
        _c("intake2_enrolment_end", "date", ROLE_REFERENCE,
           "Last date of intake 2 registration and fee payment.", "Fixed cycle template.",
           "2025-03-20", availability=AVAIL_NA),
        _c("verification_end_date", "date", ROLE_DERIVED,
           "Last day on which document verification may be completed.",
           "Derived: intake 2 application close + 4 days.", "2024-12-24", availability=AVAIL_NA),
        _c("total_weeks", "int64", ROLE_DERIVED,
           "Number of ISO weeks spanned by the cycle; the panel row count per programme-cycle.",
           "Derived: ISO weeks between cycle_start_date and cycle_end_date inclusive.", "43",
           availability=AVAIL_NA),
        _c("is_finalised", "bool", ROLE_REFERENCE,
           "True once all outcomes of the cycle are known. All cycles shipped here are finalised, "
           "so no funnel outcome is censored.",
           "Fixed constant, True for every cycle in this dataset.", "True", availability=AVAIL_NA),
        _c("total_seats_offers", "int64", ROLE_DERIVED,
           "Sum of seat capacity across all programmes in the cycle.",
           "Derived: sum of `dim_programme.base_seat_capacity`.", "1180", availability=AVAIL_NA),
    ),
)

# --------------------------------------------------------------------------------------
# dim_campaign
# --------------------------------------------------------------------------------------

dim_campaign = Entity(
    name="dim_campaign",
    grain="one row per marketing campaign within an admission cycle",
    primary_key="campaign_id",
    description="Fictional paid / owned marketing campaigns. Only channels that can be "
                "attributed to a campaign reference this table; organic, referral, direct and "
                "education-fair leads have a null `campaign_id`.",
    role_in_pipeline="Attribution / funnel-attribution analysis",
    columns=(
        _c("campaign_id", "str", ROLE_KEY, "Campaign key.", "Fixed constant dimension.",
           "CMP-2024-PAID-01", availability=AVAIL_NA),
        _c("campaign_name", "str", ROLE_REFERENCE, "Campaign name.",
           "Fixed constant dimension.", "AY2024 Prospecting - Search Brand", availability=AVAIL_NA),
        _c("channel", "str", ROLE_REFERENCE, "Channel the campaign runs on.",
           "Fixed constant dimension.", "paid_search", availability=AVAIL_NA,
           categories=ACQUISITION_CHANNELS),
        _c("cycle_id", "str", ROLE_KEY, "Admission cycle the campaign belongs to.",
           "Fixed constant dimension.", "CYC-2024", availability=AVAIL_NA,
           fk="dim_admission_cycle.cycle_id"),
        _c("start_date", "date", ROLE_REFERENCE, "Campaign start date.",
           "Fixed constant, inside the cycle application window.", "2024-06-01",
           availability=AVAIL_PRE, source_ts_field="first_touch_date"),
        _c("end_date", "date", ROLE_REFERENCE, "Campaign end date.",
           "Fixed constant, inside the cycle application window.", "2024-12-20",
           availability=AVAIL_PRE, source_ts_field="first_touch_date"),
        _c("planned_budget_inr", "int64", ROLE_GENERATED,
           "Planned campaign budget in INR.",
           "Log-normal draw per campaign, rounded to the nearest 5000 INR.", "850000",
           availability=AVAIL_PRE, source_ts_field="first_touch_date"),
        _c("target_group", "str", ROLE_REFERENCE,
           "Intended audience segment, recorded for slice-based attribution analysis.",
           "Fixed constant dimension.", "science_and_technology", availability=AVAIL_NA,
           categories=("science_and_technology", "commerce_and_management",
                       "all_programmes", "open_house_followup")),
        _c("is_active", "bool", ROLE_REFERENCE,
           "Whether the campaign ran to plan.", "Fixed constant, True for all campaigns here.",
           "True", availability=AVAIL_NA),
    ),
)

# --------------------------------------------------------------------------------------
# fact_applicant
# --------------------------------------------------------------------------------------

fact_applicant = Entity(
    name="fact_applicant",
    grain="one row per applicant",
    primary_key="applicant_id",
    description="Applicant master. Contains NO PII: no name, email, phone, address, date of birth "
                "or government identifier. `applicant_id` is a synthetic surrogate key.",
    role_in_pipeline="Entity resolution / cohort analysis; joined into the modelling view",
    columns=(
        _c("applicant_id", "str", ROLE_KEY,
           "Synthetic applicant surrogate key. Carries no external meaning.",
           "Sequential synthetic key allocated at applicant creation.", "APL-0041821",
           availability=AVAIL_NA),
        _c("region_id", "str", ROLE_KEY,
           "Applicant origin region.", "Sampled from `dim_region` enquiry shares at first "
           "inquiry, then frozen for the applicant's lifetime.",
           "REG-04", availability=AVAIL_PRE, leakage=LEAK_LOW, fk="dim_region.region_id",
           feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
           source_ts_field="inquiry_ts", source_ts_field_decision="admission_decision_ts"),
        _c("gender_band", "str", ROLE_GENERATED,
           "Self-reported gender band, synthetic. Used for programme mix and segmentation only, "
           "never as a decision variable.",
           "Categorical draw from regional base rates with a mild programme-specific mix shift "
           "applied on programme choice.", "female", availability=AVAIL_PRE, leakage=LEAK_LOW,
           feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION), categories=GENDER_BANDS,
           source_ts_field="inquiry_ts", source_ts_field_decision="admission_decision_ts"),
        _c("education_level", "str", ROLE_GENERATED,
           "Highest qualification held at the time of the first application.",
           "Categorical draw, with diploma and undergraduate candidates concentrated in "
           "management and commerce programmes.", "higher_secondary", availability=AVAIL_PRE,
           leakage=LEAK_LOW,
           feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
           categories=EDUCATION_LEVELS, source_ts_field="inquiry_ts",
           source_ts_field_decision="admission_decision_ts"),
        _c("first_inquiry_date", "date", ROLE_DERIVED,
           "Date of the applicant's first ever inquiry.", "Derived: min(inquiry_ts) over the "
           "applicant's applications.", "2023-07-14", availability=AVAIL_PRE, leakage=LEAK_LOW,
           source_ts_field="inquiry_ts", source_ts_field_decision="admission_decision_ts"),
        _c("application_count", "int64", ROLE_DERIVED,
           "Number of applications held by this applicant across all cycles.",
           "Derived: count of fact_application rows per applicant_id.", "2", availability=AVAIL_PRE,
           leakage=LEAK_LOW, feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
           source_ts_field="inquiry_ts", source_ts_field_decision="admission_decision_ts"),
        _c("is_repeat_applicant", "bool", ROLE_DERIVED,
           "True if the applicant holds more than one application across their WHOLE history, "
           "including applications made after the current prediction point. Therefore NOT a safe "
           "feature - use `fact_application.is_repeat_applicant_at_prediction` instead.",
           "Derived: application_count > 1 over all cycles.", "True", availability=AVAIL_POST,
           leakage=LEAK_HIGH),
    ),
)

# --------------------------------------------------------------------------------------
# fact_application
# --------------------------------------------------------------------------------------

_fact_application_columns = (
    # ---- keys -------------------------------------------------------------------------
    _c("application_id", "str", ROLE_KEY,
       "Synthetic application surrogate key. One row = one applicant's journey to one programme "
       "in one cycle, opened at the prospect stage.",
       "Sequential synthetic key.", "APP-0128447", availability=AVAIL_NA),
    _c("applicant_id", "str", ROLE_KEY, "Owning applicant.", "FK to fact_applicant.", "APL-0041821",
       availability=AVAIL_NA, fk="fact_applicant.applicant_id"),
    _c("programme_id", "str", ROLE_KEY, "Programme applied to.",
       "FK to dim_programme; sampled proportional to programme demand weight.",
       "PGM-07", availability=AVAIL_PRE, leakage=LEAK_LOW, fk="dim_programme.programme_id",
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="inquiry_ts", source_ts_field_decision="admission_decision_ts"),
    _c("cycle_id", "str", ROLE_KEY, "Admission cycle.",
       "FK to dim_admission_cycle.", "CYC-2024", availability=AVAIL_PRE, leakage=LEAK_LOW,
       fk="dim_admission_cycle.cycle_id",
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="inquiry_ts", source_ts_field_decision="admission_decision_ts"),
    _c("campaign_id", "str", ROLE_KEY,
       "Attributed campaign. Null unless the acquisition channel is campaign-bearing.",
       "Sampled from campaigns of the same channel and cycle whose active window contains the "
       "first touch; null for organic_search, referral, direct and education_fair.",
       "CMP-2024-PAID-01", availability=AVAIL_PRE, leakage=LEAK_LOW, nullable=True,
       fk="dim_campaign.campaign_id",
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="first_touch_date", source_ts_field_decision="admission_decision_ts"),
    # ---- attribution (pre submission) -------------------------------------------------
    _c("acquisition_channel", "str", ROLE_GENERATED,
       "First-touch acquisition channel. ASSOCIATION ONLY: differences across channels reflect "
       "different applicant mixes and must not be read as causal lift.",
       "Categorical draw from channel mix weights that drift by cycle and intake round.",
       "organic_search", availability=AVAIL_PRE, leakage=LEAK_LOW,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       categories=ACQUISITION_CHANNELS, source_ts_field="first_touch_date",
       source_ts_field_decision="admission_decision_ts"),
    _c("acquisition_source", "str", ROLE_GENERATED,
       "Specific source / sub-channel within `acquisition_channel`.",
       "Uniform draw within the chosen channel's source list.", "google_organic",
       availability=AVAIL_PRE, leakage=LEAK_LOW,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       categories=tuple(s for v in ACQUISITION_SOURCE_EXAMPLES.values() for s in v),
       source_ts_field="first_touch_date", source_ts_field_decision="admission_decision_ts"),
    _c("first_touch_date", "str", ROLE_GENERATED,
       "Date of the applicant's first recorded marketing touch. Always on or before "
       "`inquiry_ts`.",
       "inquiry_date minus a Gamma-distributed lead lag; clipped to the cycle application "
       "window.", "2024-06-14", availability=AVAIL_PRE, leakage=LEAK_LOW,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="first_touch_date", source_ts_field_decision="admission_decision_ts"),
    _c("touchpoints_count", "int64", ROLE_GENERATED,
       "Number of recorded marketing touchpoints before the inquiry.",
       "1 + Poisson(mean 2.2) with a channel-dependent rate; capped at 12.", "4",
       availability=AVAIL_PRE, leakage=LEAK_LOW,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="first_touch_date", source_ts_field_decision="admission_decision_ts"),
    _c("is_multi_touch", "bool", ROLE_GENERATED,
       "True if the prospect had more than one touchpoint before inquiring.",
       "Derived: touchpoints_count > 1.", "True", availability=AVAIL_PRE, leakage=LEAK_LOW,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="first_touch_date", source_ts_field_decision="admission_decision_ts"),
    _c("is_referral_alumni", "bool", ROLE_GENERATED,
       "True if the referral came from an alumnus.",
       "Bernoulli(0.28) when acquisition_channel == 'referral', else False.", "False",
       availability=AVAIL_PRE, leakage=LEAK_LOW,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="first_touch_date", source_ts_field_decision="admission_decision_ts"),
    # ---- applicant context (pre submission) --------------------------------------------
    _c("intake_round", "int64", ROLE_GENERATED,
       "Intake round this application belongs to, fixed at prospect creation from the inquiry "
       "date relative to the intake 1 close date. Governs the submission deadline, decision "
       "window and offer deadline that apply.",
       "1 if inquiry_date <= intake1_application_close else 2.", "1",
       availability=AVAIL_PRE, leakage=LEAK_LOW,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION), source_ts_field="inquiry_ts",
       source_ts_field_decision="admission_decision_ts"),
    _c("academic_score_pct", "float64", ROLE_GENERATED,
       "Percentage score on the qualifying examination, as reported at submission. A noisy "
       "observation of the latent ability factor (correlation approx. 0.8), so it is strongly "
       "but not perfectly informative.",
       "N(58 + 9 * z_ability + 5 * reporting_noise, 4) clipped to [40, 99], rounded to 1 dp.",
       "78.0", availability=AVAIL_AT, leakage=LEAK_LOW,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="application_submitted_ts",
       source_ts_field_decision="admission_decision_ts"),
    _c("academic_score_band", "str", ROLE_DERIVED,
       "Banded academic score. Derived ONLY from `academic_score_pct`, which is known at "
       "submission; it is not the post-decision merit score.",
       "Derived: banding of academic_score_pct.", "70_79", availability=AVAIL_AT, leakage=LEAK_LOW,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       categories=ACADEMIC_SCORE_BANDS, source_ts_field="application_submitted_ts",
       source_ts_field_decision="admission_decision_ts"),
    _c("doc_completeness_score", "float64", ROLE_GENERATED,
       "Completeness of the supporting document set as assessed at submission, in [0.15, 1.0]. "
       "Drives the probability that verification succeeds.",
       "clip(sigmoid(1.35 + 1.1 * z_ability + 0.8 * z_intent - 0.9 * log1p(1/days_available)) "
       "+ N(0, 0.08), 0.15, 1.0), rounded to 4 dp.", "0.8421", availability=AVAIL_AT,
       leakage=LEAK_LOW, feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="application_submitted_ts",
       source_ts_field_decision="admission_decision_ts"),
    _c("fee_scholarship_applied", "bool", ROLE_GENERATED,
       "True if the applicant applied for fee concession or scholarship at submission. A weak "
       "observable proxy for financial constraint; the dominant factor remains unobserved.",
       "Bernoulli depending on education level, region type and the latent financial-constraint "
       "factor.", "False", availability=AVAIL_AT, leakage=LEAK_LOW,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="application_submitted_ts",
       source_ts_field_decision="admission_decision_ts"),
    # ---- timing (pre submission / at prediction point) ---------------------------------
    _c("is_repeat_applicant_at_prediction", "bool", ROLE_DERIVED,
       "True if, at the moment this application was submitted, the applicant already held at "
       "least one other SUBMITTED application. This is the leakage-safe version of the lifetime "
       "`fact_applicant.is_repeat_applicant` flag, which must never be used as a feature.",
       "Derived in a post-pass: count distinct applicant_ids over applications with "
       "application_submitted_ts <= this application's submission timestamp, then compare > 1.",
       "False", availability=AVAIL_AT, leakage=LEAK_LOW,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="application_submitted_ts",
       source_ts_field_decision="admission_decision_ts"),
    _c("inquiry_ts", "str", ROLE_GENERATED,
       "Timestamp of the inquiry that opened this application. Equals the `prospect` funnel "
       "event timestamp.",
       "Beta-shaped draw over the intake round inquiry window, plus an intraday hour offset.",
       "2024-07-03T10:42:00", availability=AVAIL_PRE, leakage=LEAK_NONE,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION), source_ts_field="inquiry_ts",
       source_ts_field_decision="admission_decision_ts"),
    _c("application_started_ts", "str", ROLE_GENERATED,
       "Timestamp of the first form session. Equals the `application_started` funnel event "
       "timestamp. Strictly after inquiry_ts and never after the round close date.",
       "inquiry_ts + Gamma(1.4, 2.2) days, clipped to the round close date.", "2024-07-06T18:05:00",
       availability=AVAIL_PRE, leakage=LEAK_NONE,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="application_started_ts",
       source_ts_field_decision="admission_decision_ts"),
    _c("application_submitted_ts", "str", ROLE_DERIVED,
       "Timestamp of submission. Equals the `application_submitted` funnel event timestamp and "
       "IS the prediction point of the primary task.",
       "application_started_ts + Gamma(1.8, 1.9) days, clipped to the round close date; always "
       ">= 1 day after application_started_ts.", "2024-07-11T20:14:00", availability=AVAIL_AT,
       leakage=LEAK_NONE, feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="application_submitted_ts",
       source_ts_field_decision="admission_decision_ts"),
    _c("prediction_ts", "str", ROLE_DERIVED,
       "Explicit prediction timestamp for the primary task. Equal to "
       "`application_submitted_ts`; declared separately so that the leakage boundary is machine "
       "readable.",
       "Derived: alias of application_submitted_ts.", "2024-07-11T20:14:00", availability=AVAIL_AT,
       leakage=LEAK_NONE),
    _c("prediction_stage", "str", ROLE_DERIVED,
       "Funnel stage at which the primary prediction is made.", "Fixed constant.",
       "application_submitted", availability=AVAIL_AT, leakage=LEAK_NONE,
       categories=("application_submitted",)),
    _c("days_inquiry_to_start", "int64", ROLE_DERIVED,
       "Days from inquiry to first form session.", "Derived: floor of the timestamp difference.",
       "3", availability=AVAIL_PRE, leakage=LEAK_NONE,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="application_started_ts",
       source_ts_field_decision="admission_decision_ts"),
    _c("days_start_to_submit", "int64", ROLE_DERIVED,
       "Days from first form session to submission.", "Derived: floor of the timestamp "
       "difference.", "5", availability=AVAIL_AT, leakage=LEAK_NONE,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="application_submitted_ts",
       source_ts_field_decision="admission_decision_ts"),
    _c("days_inquiry_to_submit", "int64", ROLE_DERIVED,
       "Days from inquiry to submission. The single strongest behavioural summary of intent.",
       "Derived: floor of the timestamp difference.", "8", availability=AVAIL_AT, leakage=LEAK_NONE,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="application_submitted_ts",
       source_ts_field_decision="admission_decision_ts"),
    _c("days_to_round_close_at_start", "int64", ROLE_DERIVED,
       "Days remaining from the first form session to the intake round close date. Captures "
       "deadline pressure; small values strongly reduce submission probability.",
       "Derived: (round close date - date(application_started_ts)) in days.", "101",
       availability=AVAIL_PRE, leakage=LEAK_NONE,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="application_started_ts",
       source_ts_field_decision="admission_decision_ts"),
    _c("week_of_cycle_at_submission", "int64", ROLE_DERIVED,
       "ISO week index of the submission week relative to the cycle start week (0-based).",
       "Derived from submission date and cycle_start_date.", "7", availability=AVAIL_AT,
       leakage=LEAK_NONE, feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="application_submitted_ts",
       source_ts_field_decision="admission_decision_ts"),
    _c("month_of_submission", "int64", ROLE_DERIVED,
       "Calendar month of submission (1-12).", "Derived from application_submitted_ts.", "7",
       availability=AVAIL_AT, leakage=LEAK_NONE,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="application_submitted_ts",
       source_ts_field_decision="admission_decision_ts"),
    # ---- engagement summary (pre submission, derived from fact_engagement) -------------
    _c("pre_sub_session_count", "int64", ROLE_DERIVED,
       "Total pre-submission sessions in `fact_engagement`.",
       "Derived: sum of session_count over engagement rows with activity_date <= "
       "date(prediction_ts).", "9", availability=AVAIL_PRE, leakage=LEAK_NONE,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="application_submitted_ts",
       source_ts_field_decision="admission_decision_ts"),
    _c("pre_sub_active_days", "int64", ROLE_DERIVED,
       "Number of distinct pre-submission activity dates.", "Derived: count of engagement rows "
       "with activity_date <= date(prediction_ts).", "6", availability=AVAIL_PRE, leakage=LEAK_NONE,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="application_submitted_ts",
       source_ts_field_decision="admission_decision_ts"),
    _c("pre_sub_total_minutes", "float64", ROLE_DERIVED,
       "Total minutes of pre-submission portal activity.",
       "Derived: sum of total_minutes over engagement rows up to the prediction date.", "212.5",
       availability=AVAIL_PRE, leakage=LEAK_NONE,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="application_submitted_ts",
       source_ts_field_decision="admission_decision_ts"),
    _c("pre_sub_doc_uploads", "int64", ROLE_DERIVED,
       "Documents uploaded before submission.", "Derived: sum of docs_uploaded.", "4",
       availability=AVAIL_PRE, leakage=LEAK_NONE,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="application_submitted_ts",
       source_ts_field_decision="admission_decision_ts"),
    _c("pre_sub_form_fields_completed", "int64", ROLE_DERIVED,
       "Form fields completed before submission.", "Derived: sum of form_fields_completed.", "57",
       availability=AVAIL_PRE, leakage=LEAK_NONE,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="application_submitted_ts",
       source_ts_field_decision="admission_decision_ts"),
    _c("pre_sub_return_visits", "int64", ROLE_DERIVED,
       "Pre-submission sessions that were return visits (not the applicant's first session).",
       "Derived: sum of is_return_visit.", "5", availability=AVAIL_PRE, leakage=LEAK_NONE,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="application_submitted_ts",
       source_ts_field_decision="admission_decision_ts"),
    # ---- post-submission outcomes (POST_OUTCOME) --------------------------------------
    _c("stage_reached", "str", ROLE_POST_OUTCOME,
       "Highest funnel stage reached by this application. CONTAINS THE ANSWER - never a feature.",
       "Derived: max stage_order present in fact_funnel_event for this application.",
       "admitted", availability=AVAIL_POST, leakage=LEAK_HIGH, categories=STAGE_CODES),
    _c("stage_reached_order", "int64", ROLE_POST_OUTCOME,
       "Integer position of `stage_reached`. CONTAINS THE ANSWER - never a feature.",
       "Derived from fact_funnel_event.", "6", availability=AVAIL_POST, leakage=LEAK_HIGH),
    _c("dropoff_stage", "str", ROLE_POST_OUTCOME,
       "Stage at which the application left the funnel. Null when enrolled.",
       "Derived: equal to stage_reached when stage_reached != 'enrolled'.", "admitted",
       availability=AVAIL_POST, leakage=LEAK_HIGH, nullable=True, categories=STAGE_CODES),
    _c("dropoff_reason", "str", ROLE_POST_OUTCOME,
       "Single categorical reason for leaving the funnel. Null when enrolled.",
       "Categorical draw from the reason list valid for the stage where the transition failed.",
       "offer_not_accepted", availability=AVAIL_POST, leakage=LEAK_HIGH, nullable=True,
       categories=DROP_REASONS),
    _c("doc_query_raised", "bool", ROLE_POST_OUTCOME,
       "True if document clarification was requested during verification.",
       "Bernoulli from a logistic model of `doc_completeness_score`, education level and channel.",
       "True", availability=AVAIL_POST, leakage=LEAK_HIGH),
    _c("doc_query_count", "int64", ROLE_POST_OUTCOME,
       "Number of document clarification requests raised.",
       "0, or 1 + Poisson(0.4) when a query was raised.", "1", availability=AVAIL_POST,
       leakage=LEAK_HIGH),
    _c("doc_verification_status", "str", ROLE_POST_OUTCOME,
       "Verification outcome for the application.",
       "Derived from the doc-query sub-process: verified / returned_for_correction / "
       "rejected_ineligible / not_initiated.", "verified", availability=AVAIL_POST,
       leakage=LEAK_HIGH, categories=DOC_VERIFICATION_STATUSES),
    _c("application_verified_ts", "str", ROLE_POST_OUTCOME,
       "Timestamp at which verification was granted. Strictly after submission.",
       "submission + programme review duration * lognormal noise + any doc-query delay.",
       "2024-07-20T15:31:00", availability=AVAIL_POST, leakage=LEAK_HIGH, nullable=True),
    _c("admission_decision_ts", "str", ROLE_POST_OUTCOME,
       "Timestamp at which the decision was released.",
       "Intake decision window start + programme offset (0-10 days) + jitter (0-2 days), pushed "
       "later if verification finished after the window opened.", "2024-11-22T11:00:00",
       availability=AVAIL_POST, leakage=LEAK_HIGH, nullable=True),
    _c("admitted_ts", "str", ROLE_POST_OUTCOME,
       "Timestamp at which the offer was dispatched and the seat confirmed. Strictly after "
       "`admission_decision_ts` (contract invariant F2).",
       "decision_ts + Uniform(3, 60) hours - the offer is issued by admissions after the "
       "committee decision is released.", "2024-11-23T14:20:00", availability=AVAIL_POST,
       leakage=LEAK_HIGH, nullable=True),
    _c("enrolled_ts", "str", ROLE_POST_OUTCOME,
       "Timestamp at which registration and first fee instalment were completed. THE ANSWER.",
       "admitted_ts + Gamma(2.2, 5.5) days, truncated at the round offer deadline; null when the "
       "offer was not accepted in time.", "2024-12-18T09:12:00", availability=AVAIL_POST,
       leakage=LEAK_HIGH, nullable=True),
    _c("days_submitted_to_verified", "int64", ROLE_POST_OUTCOME,
       "Days from submission to verification.", "Derived: floor of the timestamp difference.",
       "9", availability=AVAIL_POST, leakage=LEAK_HIGH, nullable=True),
    _c("days_verified_to_decision", "int64", ROLE_POST_OUTCOME,
       "Days from verification to decision release.", "Derived: floor of the timestamp "
       "difference.", "64", availability=AVAIL_POST, leakage=LEAK_HIGH, nullable=True),
    _c("days_decision_to_enrolled", "int64", ROLE_POST_OUTCOME,
       "Days from decision to enrolment for admitted applicants.",
       "Derived: floor of the timestamp difference.", "26", availability=AVAIL_POST,
       leakage=LEAK_HIGH, nullable=True),
    _c("decision_type", "str", ROLE_POST_OUTCOME,
       "Formal decision released. THE DECISION ITSELF - never a feature.",
       "Bernoulli from the programme/cycle merit model, or 'reject' if verification failed or "
       "the applicant withdrew.", "admit", availability=AVAIL_POST, leakage=LEAK_HIGH,
       nullable=True, categories=DECISION_TYPES),
    _c("selection_score", "float64", ROLE_POST_OUTCOME,
       "The institution's internal merit score, computed at decision time from transcripts, "
       "eligibility and category. THIS IS THE DELIBERATE LEAKAGE TRAP: it is the single "
       "strongest predictor of the decision and does not exist at submission. Retained in the "
       "raw table on purpose; the validator fails if it enters a feature set.",
       "Derived from academic_score_pct, education level, programme quota mix and the latent "
       "ability factor; only defined for applications that reached a decision.", "78.42",
       availability=AVAIL_POST, leakage=LEAK_HIGH, nullable=True),
    _c("offer_letter_issued", "bool", ROLE_POST_OUTCOME,
       "True if an offer letter was issued.", "Derived: decision_type == 'admit'.", "True",
       availability=AVAIL_POST, leakage=LEAK_HIGH),
    _c("offer_deadline", "str", ROLE_POST_OUTCOME,
       "Last date the offer could be accepted.", "Round offer deadline + programme jitter of "
       "0-4 days.", "2025-01-10", availability=AVAIL_POST, leakage=LEAK_HIGH, nullable=True),
    _c("scholarship_offered", "bool", ROLE_POST_OUTCOME,
       "True if a fee concession accompanied the offer.",
       "Bernoulli from merit margin and programme scholarship budget.", "False",
       availability=AVAIL_POST, leakage=LEAK_HIGH),
    _c("scholarship_amount_inr", "int64", ROLE_POST_OUTCOME,
       "Annual concession amount in INR. Zero when no scholarship was offered.",
       "0 when not offered, else a draw scaled by merit margin and fee.", "0",
       availability=AVAIL_POST, leakage=LEAK_HIGH, nullable=True),
    _c("withdrawn_flag", "bool", ROLE_POST_OUTCOME,
       "True if the applicant withdrew after submission.",
       "Bernoulli(0.018) between verification and the decision window.", "False",
       availability=AVAIL_POST, leakage=LEAK_HIGH),
    _c("withdrawn_date", "str", ROLE_POST_OUTCOME,
       "Date of withdrawal. Null when the applicant did not withdraw.",
       "verified_ts + Uniform(1, 20) days when withdrawn.", "", availability=AVAIL_POST,
       leakage=LEAK_HIGH, nullable=True),
    # ---- targets -----------------------------------------------------------------------
    _c("admitted_flag", "int64", ROLE_POST_OUTCOME,
       "1 if the applicant was admitted. STRUCTURALLY FORBIDDEN as a feature: it is an "
       "intermediate outcome of the primary target and a legitimate secondary target for an "
       "admission-offer model.",
       "Derived: stage_reached_order >= 6.", "1", availability=AVAIL_POST, leakage=LEAK_HIGH,
       secondary_target=True),
    _c("enrolled_given_admitted_flag", "int64", ROLE_TARGET,
       "Conditional target: 1 if an ADMITTED applicant went on to enrol. Null for applications "
       "that never reached `admitted`. Predicted at `admission_decision_ts` using the `decision` "
       "feature set.",
       "Derived: 1 if stage_reached_order == 7, else 0 for admitted, null otherwise.", "1",
       availability=AVAIL_POST, leakage=LEAK_HIGH, nullable=True),
    _c("enrolled_flag", "int64", ROLE_TARGET,
       "PRIMARY TARGET. 1 if the applicant completed registration for this programme in this "
       "cycle. Predicted at `application_submitted_ts` using the `primary` feature set.",
       "Derived: 1 if stage_reached_order == 7 else 0.", "1", availability=AVAIL_POST,
       leakage=LEAK_HIGH, secondary_target=True),
    # ---- grouping / bookkeeping -------------------------------------------------------
    _c("cohort_label", "str", ROLE_DERIVED,
       "Programme x cycle cohort key used for cohort analysis and dashboards.",
       "Derived: programme_code + '-' + cycle_id.", "BSC-CS-CYC-2024", availability=AVAIL_PRE,
       leakage=LEAK_LOW, feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       source_ts_field="inquiry_ts", source_ts_field_decision="admission_decision_ts"),
    _c("split_hint", "str", ROLE_DERIVED,
       "Chronological split hint derived ONLY from `cycle_id` (earliest cycles train, latest "
       "test). Never a function of the target.",
       "Deterministic mapping of sorted cycle_id to train / validation / test.", "train",
       availability=AVAIL_PRE, leakage=LEAK_LOW,
       feature_sets=(FEATURE_SET_PRIMARY, FEATURE_SET_DECISION),
       categories=SPLIT_HINTS, source_ts_field="inquiry_ts",
       source_ts_field_decision="admission_decision_ts"),
)

fact_application = Entity(
    name="fact_application",
    grain="one row per applicant's application journey to one programme in one admission cycle, "
          "opened at the prospect stage",
    primary_key="application_id",
    description="The central fact table and the unit of record for the whole project. Carries "
                "pre-submission features, the explicit prediction point, the post-submission "
                "funnel outcome and the targets.",
    role_in_pipeline="Primary ML unit; funnel analytics grain; source of the modelling view",
    columns=_fact_application_columns,
)

# --------------------------------------------------------------------------------------
# fact_funnel_event
# --------------------------------------------------------------------------------------

fact_funnel_event = Entity(
    name="fact_funnel_event",
    grain="one row per application per achieved funnel stage (at most 7 rows per application)",
    primary_key="event_id",
    description="Event-level ladder of funnel milestones. Prefix-closed and strictly "
                "chronological by contract (invariants F1, F2).",
    role_in_pipeline="Funnel analytics, conversion and drop-off analysis, forecast panel input",
    columns=(
        _c("event_id", "str", ROLE_KEY, "Funnel event key.", "Sequential synthetic key.",
           "FEV-0093112", availability=AVAIL_NA),
        _c("application_id", "str", ROLE_KEY, "Application the milestone belongs to.",
           "FK to fact_application.", "APP-0128447", availability=AVAIL_NA,
           fk="fact_application.application_id"),
        _c("programme_id", "str", ROLE_KEY, "Denormalised programme (partition/join key).",
           "Copied from fact_application for panel aggregation without a join.", "PGM-07",
           availability=AVAIL_NA, fk="dim_programme.programme_id"),
        _c("cycle_id", "str", ROLE_KEY, "Denormalised admission cycle (partition key).",
           "Copied from fact_application.", "CYC-2024", availability=AVAIL_NA,
           fk="dim_admission_cycle.cycle_id"),
        _c("stage_code", "str", ROLE_KEY, "Stage achieved.",
           "FK to dim_funnel_stage.", "application_submitted", availability=AVAIL_NA,
           categories=STAGE_CODES, fk="dim_funnel_stage.stage_code"),
        _c("stage_order", "int64", ROLE_DERIVED, "Integer ladder position of the stage.",
           "Derived: lookup of stage_code in dim_funnel_stage.", "3", availability=AVAIL_NA),
        _c("intake_round", "int64", ROLE_DERIVED, "Intake round of the owning application.",
           "Copied from fact_application.", "1", availability=AVAIL_NA),
        _c("event_ts", "str", ROLE_GENERATED, "Milestone timestamp.",
           "Draw from the stage-specific timing mechanism documented on the corresponding "
           "fact_application column.", "2024-07-11T20:14:00", availability=AVAIL_NA),
        _c("event_date", "str", ROLE_DERIVED, "Calendar date of the milestone.",
           "Derived: date part of event_ts.", "2024-07-11", availability=AVAIL_NA),
        _c("days_since_prev_stage", "int64", ROLE_DERIVED,
           "Days elapsed since the previous achieved milestone. Null for the first stage.",
           "Derived: floor of the difference between consecutive milestones.", "5",
           availability=AVAIL_NA, nullable=True),
        _c("is_terminal_stage", "bool", ROLE_DERIVED,
           "True for the single highest stage the application reached.",
           "Derived: stage_order == stage_reached_order of the application.", "False",
           availability=AVAIL_NA),
    ),
)

# --------------------------------------------------------------------------------------
# fact_engagement
# --------------------------------------------------------------------------------------

fact_engagement = Entity(
    name="fact_engagement",
    grain="one row per application per activity date, within the pre-submission window",
    primary_key="engagement_id",
    description="Daily aggregate of portal activity between the first form session and the "
                "prediction point. Exists only for applications that reached "
                "`application_started`.",
    role_in_pipeline="Behavioural features; funnel progression explanation; explainability",
    columns=(
        _c("engagement_id", "str", ROLE_KEY, "Engagement row key.", "Sequential synthetic key.",
           "ENG-0442108", availability=AVAIL_NA),
        _c("application_id", "str", ROLE_KEY, "Application the activity belongs to.",
           "FK to fact_application.", "APP-0128447", availability=AVAIL_NA,
           fk="fact_application.application_id"),
        _c("cycle_id", "str", ROLE_KEY, "Denormalised admission cycle.", "Copied from "
           "fact_application.", "CYC-2024", availability=AVAIL_NA,
           fk="dim_admission_cycle.cycle_id"),
        _c("activity_date", "str", ROLE_GENERATED,
           "Date of portal activity. Always on or before date(application_submitted_ts) for "
           "submitted applications, which is what makes the derived pre-submission aggregates "
           "safe features.",
           "Uniform draw over the active window, conditioned on the latent engagement intensity.",
           "2024-07-08", availability=AVAIL_NA),
        _c("days_before_submission", "int64", ROLE_DERIVED,
           "Days between the activity and the prediction point. Null when the application was "
           "never submitted (no prediction point exists).",
           "Derived: (date(application_submitted_ts) - activity_date) in days.", "3",
           availability=AVAIL_NA, nullable=True),
        _c("session_count", "int64", ROLE_GENERATED, "Sessions on the activity date.",
           "1 + Poisson(0.9) on active days, 1 on the first session day.", "2",
           availability=AVAIL_NA),
        _c("total_minutes", "float64", ROLE_GENERATED, "Minutes of activity on the date.",
           "Log-normal around the latent engagement intensity, rounded to 1 dp.", "27.4",
           availability=AVAIL_NA),
        _c("pages_viewed", "int64", ROLE_GENERATED, "Programme pages viewed on the date.",
           "Poisson(2.2) scaled by engagement intensity.", "6", availability=AVAIL_NA),
        _c("docs_uploaded", "int64", ROLE_GENERATED, "Documents uploaded on the date.",
           "Poisson(0.5) scaled by engagement intensity, capped at 4.", "1",
           availability=AVAIL_NA),
        _c("form_fields_completed", "int64", ROLE_GENERATED, "Form fields completed on the date.",
           "Poisson(3.5) scaled by engagement intensity, capped at 14.", "9", availability=AVAIL_NA),
        _c("device_type", "str", ROLE_GENERATED, "Dominant device for the day's sessions.",
           "Categorical draw with a mobile-heavy base mix.", "mobile", availability=AVAIL_NA,
           categories=DEVICE_TYPES),
        _c("is_return_visit", "bool", ROLE_GENERATED,
           "True if the day's sessions were a return to the form rather than the first session.",
           "Deterministic: False on the first activity date, True afterwards.", "True",
           availability=AVAIL_NA),
    ),
)

# --------------------------------------------------------------------------------------
# fact_forecast_panel
# --------------------------------------------------------------------------------------

_panel_cum = (
    ("cum_applications_opened", "Cumulative applications opened (stage `prospect`) as at the end "
                               "of the week."),
    ("cum_applications_started", "Cumulative applications started (stage "
                                "`application_started`) as at the end of the week."),
    ("cum_applications_submitted", "Cumulative applications submitted (stage "
                                   "`application_submitted`) as at the end of the week."),
    ("cum_applications_verified", "Cumulative applications verified (stage "
                                  "`application_verified`) as at the end of the week."),
    ("cum_decisions_issued", "Cumulative decisions released (stage `admission_decision`) as at "
                             "the end of the week."),
    ("cum_admitted", "Cumulative admitted (stage `admitted`) as at the end of the week."),
    ("cum_enrolled", "Cumulative enrolled (stage `enrolled`) as at the end of the week. PRIMARY "
                     "FORECAST QUANTITY."),
)
_panel_wk = (
    ("wk_applications_submitted", "Applications submitted during the week."),
    ("wk_applications_verified", "Applications verified during the week."),
    ("wk_decisions_issued", "Decisions released during the week."),
    ("wk_admitted", "Admitted during the week."),
    ("wk_enrolled", "Enrolled during the week."),
)

fact_forecast_panel = Entity(
    name="fact_forecast_panel",
    grain="one row per programme x admission cycle x ISO week (Monday start)",
    primary_key="panel_id",
    description="Regular weekly panel of cumulative funnel counts. This is the forecasting and "
                "scenario-simulation surface. Contains no forward-looking column: every value is "
                "an as-at-week count.",
    role_in_pipeline="Forecasting (T-F), yield-curve analytics, scenario simulation",
    columns=(
        _c("panel_id", "str", ROLE_KEY, "Panel cell key.", "programme_id + cycle_id + "
           "week_start_date.", "PGM-07|CYC-2024|2024-06-03", availability=AVAIL_NA),
        _c("programme_id", "str", ROLE_KEY, "Programme.", "FK to dim_programme.", "PGM-07",
           availability=AVAIL_NA, fk="dim_programme.programme_id"),
        _c("cycle_id", "str", ROLE_KEY, "Admission cycle.", "FK to dim_admission_cycle.",
           "CYC-2024", availability=AVAIL_NA, fk="dim_admission_cycle.cycle_id"),
        _c("week_start_date", "str", ROLE_DERIVED, "Monday of the ISO week.",
           "Derived: Monday of the week containing the date.", "2024-06-03", availability=AVAIL_NA),
        _c("week_end_date", "str", ROLE_DERIVED, "Sunday of the ISO week.",
           "Derived: week_start_date + 6 days.", "2024-06-09", availability=AVAIL_NA),
        _c("week_index_in_cycle", "int64", ROLE_DERIVED,
           "0-based ISO week index from the cycle start week.",
           "Derived: whole weeks between cycle start week and this week.", "0",
           availability=AVAIL_NA),
        _c("is_forecast_eligible", "bool", ROLE_DERIVED,
           "True when this week can serve as a forecast origin for the enrolled-yield task: at "
           "least 4 weeks of history, on or after the first decision window opens, and on or "
           "before the cycle enrolment end date.",
           "Derived from week_index_in_cycle and the cycle calendar.", "False",
           availability=AVAIL_NA),
        _c("split_hint", "str", ROLE_DERIVED,
           "Chronological split hint derived only from cycle_id.",
           "Deterministic mapping of sorted cycle_id to train / validation / test.", "train",
           availability=AVAIL_NA, categories=SPLIT_HINTS),
        _c("n_applications", "int64", ROLE_DERIVED,
           "Number of application rows in the cell's programme-cycle, for denominator checks.",
           "Derived: count of fact_application per programme-cycle.", "0", availability=AVAIL_NA),
    )
    + tuple(
        _c(name, "int64", ROLE_DERIVED, desc + " Derived: running count of the corresponding "
           "funnel events whose event_date falls on or before week_end_date.",
           "742", availability=AVAIL_NA)
        for name, desc in _panel_cum
    )
    + tuple(
        _c(name, "int64", ROLE_DERIVED, desc + " Derived: count of events whose event_date falls "
           "inside [week_start_date, week_end_date].",
           "41", availability=AVAIL_NA)
        for name, desc in _panel_wk
    )
    + (
        _c("cum_submit_to_verify_rate", "float64", ROLE_DERIVED,
           "cum_applications_verified / cum_applications_submitted. NULL while the denominator "
           "is zero.",
           "Derived ratio, rounded to 6 dp.", "0.7612", availability=AVAIL_NA, nullable=True),
        _c("cum_admit_rate", "float64", ROLE_DERIVED,
           "cum_admitted / cum_decisions_issued. NULL while the denominator is zero.",
           "Derived ratio, rounded to 6 dp.", "0.5127", availability=AVAIL_NA, nullable=True),
        _c("cum_enrolment_yield", "float64", ROLE_DERIVED,
           "cum_enrolled / cum_applications_submitted. The headline yield metric of the project. "
           "NULL while the denominator is zero.",
           "Derived ratio, rounded to 6 dp.", "0.2531", availability=AVAIL_NA, nullable=True),
    ),
)

# --------------------------------------------------------------------------------------
# Entity registry
# --------------------------------------------------------------------------------------

ENTITIES: Dict[str, Entity] = {
    e.name: e
    for e in (
        dim_funnel_stage,
        dim_region,
        dim_programme,
        dim_admission_cycle,
        dim_campaign,
        fact_applicant,
        fact_application,
        fact_funnel_event,
        fact_engagement,
        fact_forecast_panel,
    )
}

RAW_TABLES: Tuple[str, ...] = tuple(ENTITIES.keys())

FOREIGN_KEYS: Tuple[Tuple[str, str, str, str], ...] = tuple(
    (entity.name, col.name, col.fk.split(".")[0], col.fk.split(".")[1])
    for entity in ENTITIES.values()
    for col in entity.columns
    if col.fk
)

PRIMARY_KEYS: Dict[str, str] = {e.name: e.primary_key for e in ENTITIES.values()}

# --------------------------------------------------------------------------------------
# Feature sets (allow-lists)
# --------------------------------------------------------------------------------------


def feature_columns(feature_set: str) -> List[Tuple[str, str]]:
    """Return [(entity, column)] for a feature set, ordered for reproducible output."""
    if feature_set not in FEATURE_SETS:
        raise ValueError(f"unknown feature set {feature_set}")
    out: List[Tuple[str, str]] = []
    for e in ENTITIES.values():
        for c in e.columns:
            if feature_set in c.feature_sets:
                out.append((e.name, c.name))
    return out


def post_outcome_columns() -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for e in ENTITIES.values():
        for c in e.columns:
            if c.role in (ROLE_POST_OUTCOME, ROLE_TARGET):
                out.append((e.name, c.name))
    return out


def target_columns() -> List[Tuple[str, str]]:
    return [(e.name, c.name) for e in ENTITIES.values() for c in e.columns if c.role == ROLE_TARGET]


def secondary_target_columns() -> List[Tuple[str, str]]:
    return [(e.name, c.name) for e in ENTITIES.values()
            for c in e.columns if c.role in (ROLE_TARGET, ROLE_POST_OUTCOME) and c.secondary_target]


def source_ts_field(entity: str, column: str, feature_set: str) -> Optional[str]:
    col = ENTITIES[entity].col(column)
    if feature_set == FEATURE_SET_DECISION and col.source_ts_field_decision:
        return col.source_ts_field_decision
    return col.source_ts_field


def prediction_point_column(feature_set: str) -> str:
    return "application_submitted_ts" if feature_set == FEATURE_SET_PRIMARY \
        else "admission_decision_ts"


# --------------------------------------------------------------------------------------
# Denormalised modelling view (data/processed/applications_modelling_view.csv)
# --------------------------------------------------------------------------------------

MV_DESCRIPTION = (
    "Deterministic denormalised extract used for the primary supervised task. Built entirely by "
    "the generator from the raw tables; it is not hand-edited. Population: applications that "
    "reached `application_submitted`, i.e. rows that have a prediction point."
)

MV_COLUMNS: Tuple[MVColumn, ...] = (
    MVColumn("application_id", "fact_application", "application_id",
             "Synthetic application key. Join key, not a feature.", ROLE_KEY, AVAIL_NA, LEAK_NONE,
             False, False),
    MVColumn("applicant_id", "fact_applicant", "applicant_id",
             "Synthetic applicant key. Join key, not a feature.", ROLE_KEY, AVAIL_NA, LEAK_NONE,
             False, False),
    MVColumn("programme_id", "fact_application", "programme_id",
             "Programme applied to.", ROLE_GENERATED, AVAIL_PRE, LEAK_LOW, True, True),
    MVColumn("cycle_id", "fact_application", "cycle_id",
             "Admission cycle.", ROLE_GENERATED, AVAIL_PRE, LEAK_LOW, True, True),
    MVColumn("cohort_label", "fact_application", "cohort_label",
             "Programme x cycle cohort key.", ROLE_DERIVED, AVAIL_PRE, LEAK_LOW, True, True),
    MVColumn("split_hint", "fact_application", "split_hint",
             "Chronological split hint from cycle_id only.", ROLE_DERIVED, AVAIL_PRE, LEAK_LOW,
             True, True),
    MVColumn("acquisition_channel", "fact_application", "acquisition_channel",
             "First-touch acquisition channel (association only, not causal).", ROLE_GENERATED,
             AVAIL_PRE, LEAK_LOW, True, True),
    MVColumn("acquisition_source", "fact_application", "acquisition_source",
             "Sub-channel within the acquisition channel.", ROLE_GENERATED, AVAIL_PRE, LEAK_LOW,
             True, True),
    MVColumn("campaign_id", "fact_application", "campaign_id",
             "Attributed campaign, null for non-campaign channels.", ROLE_GENERATED, AVAIL_PRE,
             LEAK_LOW, True, True),
    MVColumn("first_touch_date", "fact_application", "first_touch_date",
             "First recorded marketing touch date.", ROLE_GENERATED, AVAIL_PRE, LEAK_LOW, True,
             True),
    MVColumn("touchpoints_count", "fact_application", "touchpoints_count",
             "Marketing touchpoints before inquiry.", ROLE_GENERATED, AVAIL_PRE, LEAK_LOW, True,
             True),
    MVColumn("is_multi_touch", "fact_application", "is_multi_touch",
             "More than one pre-inquiry touchpoint.", ROLE_GENERATED, AVAIL_PRE, LEAK_LOW, True,
             True),
    MVColumn("is_referral_alumni", "fact_application", "is_referral_alumni",
             "Referral originated from an alumnus.", ROLE_GENERATED, AVAIL_PRE, LEAK_LOW, True,
             True),
    MVColumn("region_id", "fact_applicant", "region_id", "Applicant origin region.",
             ROLE_GENERATED, AVAIL_PRE, LEAK_LOW, True, True),
    MVColumn("region_name", "dim_region", "region_name", "Region name.", ROLE_REFERENCE,
             AVAIL_PRE, LEAK_LOW, True, True),
    MVColumn("region_type", "dim_region", "region_type", "Settlement type.", ROLE_REFERENCE,
             AVAIL_PRE, LEAK_LOW, True, True),
    MVColumn("mean_distance_km_to_campus", "dim_region", "mean_distance_km_to_campus",
             "Mean travel distance to campus; proxy for relocation cost.", ROLE_GENERATED,
             AVAIL_PRE, LEAK_LOW, True, True),
    MVColumn("gender_band", "fact_applicant", "gender_band",
             "Synthetic gender band. Segmentation only, never a decision variable.",
             ROLE_GENERATED, AVAIL_PRE, LEAK_LOW, True, True),
    MVColumn("education_level", "fact_applicant", "education_level",
             "Highest qualification held at first application.", ROLE_GENERATED, AVAIL_PRE,
             LEAK_LOW, True, True),
    MVColumn("is_repeat_applicant_at_prediction", "fact_application",
             "is_repeat_applicant_at_prediction",
             "Applicant already held another submitted application at this prediction point. The "
             "leakage-safe version of the lifetime repeat flag.",
             ROLE_DERIVED, AVAIL_AT, LEAK_LOW, True, True),
    MVColumn("selectivity_tier", "dim_programme", "selectivity_tier",
             "Published selectivity band.", ROLE_REFERENCE, AVAIL_PRE, LEAK_LOW, True, True),
    MVColumn("duration_years", "dim_programme", "duration_years", "Programme duration.",
             ROLE_GENERATED, AVAIL_PRE, LEAK_LOW, True, True),
    MVColumn("annual_fee_inr", "dim_programme", "annual_fee_inr", "Published annual fee.",
             ROLE_GENERATED, AVAIL_PRE, LEAK_LOW, True, True),
    MVColumn("base_seat_capacity", "dim_programme", "base_seat_capacity",
             "Approved intake capacity.", ROLE_GENERATED, AVAIL_PRE, LEAK_LOW, True, True),
    MVColumn("review_duration_days", "dim_programme", "review_duration_days",
             "Median submission-to-verification duration.", ROLE_GENERATED, AVAIL_PRE, LEAK_LOW,
             True, True),
    MVColumn("demand_weight", "dim_programme", "demand_weight",
             "Published relative programme attractiveness.", ROLE_GENERATED, AVAIL_PRE, LEAK_LOW,
             True, True),
    MVColumn("campus_region_id", "dim_programme", "campus_region_id", "Region of the campus.",
             ROLE_GENERATED, AVAIL_PRE, LEAK_LOW, True, True),
    MVColumn("intake_round", "fact_application", "intake_round", "Intake round.", ROLE_GENERATED,
             AVAIL_PRE, LEAK_LOW, True, True),
    MVColumn("academic_score_pct", "fact_application", "academic_score_pct",
             "Qualifying examination score, reported at submission.", ROLE_GENERATED, AVAIL_AT,
             LEAK_LOW, True, True),
    MVColumn("academic_score_band", "fact_application", "academic_score_band",
             "Banded academic score (from the submission-time score only).", ROLE_DERIVED,
             AVAIL_AT, LEAK_LOW, True, True),
    MVColumn("doc_completeness_score", "fact_application", "doc_completeness_score",
             "Document completeness at submission.", ROLE_GENERATED, AVAIL_AT, LEAK_LOW, True, True),
    MVColumn("fee_scholarship_applied", "fact_application", "fee_scholarship_applied",
             "Fee concession applied for at submission.", ROLE_GENERATED, AVAIL_AT, LEAK_LOW, True,
             True),
    MVColumn("inquiry_ts", "fact_application", "inquiry_ts", "Inquiry timestamp.", ROLE_GENERATED,
             AVAIL_PRE, LEAK_NONE, True, True),
    MVColumn("application_started_ts", "fact_application", "application_started_ts",
             "First form session timestamp.", ROLE_GENERATED, AVAIL_PRE, LEAK_NONE, True, True),
    MVColumn("application_submitted_ts", "fact_application", "application_submitted_ts",
             "Submission timestamp. THE PREDICTION POINT.", ROLE_DERIVED, AVAIL_AT, LEAK_NONE,
             True, True),
    MVColumn("days_inquiry_to_start", "fact_application", "days_inquiry_to_start",
             "Days from inquiry to first session.", ROLE_DERIVED, AVAIL_PRE, LEAK_NONE, True, True),
    MVColumn("days_start_to_submit", "fact_application", "days_start_to_submit",
             "Days from first session to submission.", ROLE_DERIVED, AVAIL_AT, LEAK_NONE, True,
             True),
    MVColumn("days_inquiry_to_submit", "fact_application", "days_inquiry_to_submit",
             "Days from inquiry to submission.", ROLE_DERIVED, AVAIL_AT, LEAK_NONE, True, True),
    MVColumn("days_to_round_close_at_start", "fact_application",
             "days_to_round_close_at_start", "Days from first session to the round close date.",
             ROLE_DERIVED, AVAIL_PRE, LEAK_NONE, True, True),
    MVColumn("week_of_cycle_at_submission", "fact_application", "week_of_cycle_at_submission",
             "ISO week index of submission within the cycle.", ROLE_DERIVED, AVAIL_AT, LEAK_NONE,
             True, True),
    MVColumn("month_of_submission", "fact_application", "month_of_submission",
             "Calendar month of submission.", ROLE_DERIVED, AVAIL_AT, LEAK_NONE, True, True),
    MVColumn("pre_sub_session_count", "fact_application", "pre_sub_session_count",
             "Pre-submission sessions.", ROLE_DERIVED, AVAIL_PRE, LEAK_NONE, True, True),
    MVColumn("pre_sub_active_days", "fact_application", "pre_sub_active_days",
             "Distinct pre-submission activity dates.", ROLE_DERIVED, AVAIL_PRE, LEAK_NONE, True,
             True),
    MVColumn("pre_sub_total_minutes", "fact_application", "pre_sub_total_minutes",
             "Pre-submission activity minutes.", ROLE_DERIVED, AVAIL_PRE, LEAK_NONE, True, True),
    MVColumn("pre_sub_doc_uploads", "fact_application", "pre_sub_doc_uploads",
             "Documents uploaded pre-submission.", ROLE_DERIVED, AVAIL_PRE, LEAK_NONE, True, True),
    MVColumn("pre_sub_form_fields_completed", "fact_application", "pre_sub_form_fields_completed",
             "Form fields completed pre-submission.", ROLE_DERIVED, AVAIL_PRE, LEAK_NONE, True,
             True),
    MVColumn("pre_sub_return_visits", "fact_application", "pre_sub_return_visits",
             "Pre-submission return visits.", ROLE_DERIVED, AVAIL_PRE, LEAK_NONE, True, True),
    # decision-view-only features
    MVColumn("admission_decision_ts", "fact_application", "admission_decision_ts",
             "Decision timestamp. It is the PREDICTION POINT of the secondary decision view, not "
             "a feature; never usable for the primary task.", ROLE_POST_OUTCOME, AVAIL_POST,
             LEAK_HIGH, False, False),
    MVColumn("application_verified_ts", "fact_application", "application_verified_ts",
             "Verification timestamp. NOT a primary feature; available at the decision point.",
             ROLE_POST_OUTCOME, AVAIL_POST, LEAK_HIGH, False, True),
    MVColumn("doc_verification_status", "fact_application", "doc_verification_status",
             "Verification outcome. NOT a primary feature; available at the decision point.",
             ROLE_POST_OUTCOME, AVAIL_POST, LEAK_HIGH, False, True),
    MVColumn("doc_query_raised", "fact_application", "doc_query_raised",
             "Document query raised. NOT a primary feature; available at the decision point.",
             ROLE_POST_OUTCOME, AVAIL_POST, LEAK_HIGH, False, True),
    MVColumn("doc_query_count", "fact_application", "doc_query_count",
             "Document query count. NOT a primary feature; available at the decision point.",
             ROLE_POST_OUTCOME, AVAIL_POST, LEAK_HIGH, False, True),
    MVColumn("days_submitted_to_verified", "fact_application", "days_submitted_to_verified",
             "Submission-to-verification days. NOT a primary feature; known at the decision "
             "point.", ROLE_POST_OUTCOME, AVAIL_POST, LEAK_HIGH, False, True),
    # outcomes and targets
    MVColumn("stage_reached", "fact_application", "stage_reached",
             "Highest stage reached. POST_OUTCOME.", ROLE_POST_OUTCOME, AVAIL_POST, LEAK_HIGH,
             False, False),
    MVColumn("stage_reached_order", "fact_application", "stage_reached_order",
             "Ladder position of stage_reached. POST_OUTCOME.", ROLE_POST_OUTCOME, AVAIL_POST,
             LEAK_HIGH, False, False),
    MVColumn("admitted_flag", "fact_application", "admitted_flag",
             "Secondary target for admission-offer prediction. POST_OUTCOME, never a feature of "
             "enrolled_flag.", ROLE_POST_OUTCOME, AVAIL_POST, LEAK_HIGH, False, False),
    MVColumn("enrolled_given_admitted_flag", "fact_application", "enrolled_given_admitted_flag",
             "Conditional secondary target, predicted at the decision point.", ROLE_TARGET,
             AVAIL_POST, LEAK_HIGH, False, False),
    MVColumn("enrolled_flag", "fact_application", "enrolled_flag",
             "PRIMARY TARGET. Registration completed for this programme in this cycle.",
             ROLE_TARGET, AVAIL_POST, LEAK_HIGH, False, False),
)


# --------------------------------------------------------------------------------------
# Data dictionary rendering
# --------------------------------------------------------------------------------------

_ROLE_MEANING = {
    ROLE_KEY: "Primary or foreign key.",
    ROLE_REFERENCE: "Published reference attribute of a dimension table. Not simulated output.",
    ROLE_GENERATED: "Drawn by the generator from the stated mechanism.",
    ROLE_DERIVED: "Computed deterministically from other columns of this dataset.",
    ROLE_TARGET: "A supervised prediction target. Forbidden as a feature.",
    ROLE_POST_OUTCOME: "Known only after the prediction point. FORBIDDEN as a feature of the "
                       "primary target.",
}


def _md_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _fmt_categories(cats: Optional[Sequence[str]], limit: int = 24) -> str:
    if not cats:
        return ""
    shown = list(cats[:limit])
    text = ", ".join(f"`{c}`" for c in shown)
    if len(cats) > limit:
        text += f", … (+{len(cats) - limit} more)"
    return text


def _column_rows(entity: Entity) -> List[str]:
    rows: List[str] = []
    for c in entity.columns:
        example = _md_escape(c.example) if c.example else "—"
        values = _fmt_categories(c.categories)
        req = "no (nullable)" if c.nullable else ("yes" if c.required else "no")
        feature = ", ".join(f"`{f}`" for f in c.feature_sets) if c.feature_sets else "—"
        src = c.source_ts_field or "—"
        example_cell = f"{example}<br>{values}" if values else example
        rows.append(
            f"| `{c.name}` | `{c.dtype}` | {c.role} | {_md_escape(entity.grain)} | {req} | "
            f"{c.availability} | `{c.source_ts_field or ''}` | {c.leakage} | {feature} | "
            f"{_md_escape(c.description)} | {_md_escape(c.generation_logic)} | {example_cell} |"
        )
    return rows


_TABLE_HEADER = (
    "| Field | Type | Role | Row grain | Required | Availability at prediction point | "
    "Source timestamp | Leakage risk | In feature set | Description | Generation logic | "
    "Example / allowed values |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|---|"
)


def render_data_dictionary(examples: Optional[Dict[Tuple[str, str], str]] = None) -> str:
    """Render docs/data_dictionary.md from the registry.

    `examples` maps (entity, column) -> a real example value taken from the generated data, so the
    documented examples can never drift from the actual dataset.
    """
    ex = examples or {}

    def ex_of(c: Column) -> str:
        return ex.get(("__current__", c.name), c.example)

    out: List[str] = []
    out.append("# AdmitFlow — Data Dictionary\n")
    out.append(
        "Rendered from `scripts/admitflow_schema.py`, the single source of truth for the column "
        "registry. Every column of every generated table is listed with its classification, "
        "prediction-time availability, leakage risk, feature-set membership and generation "
        "logic. If a column exists in the data but not in this file, the dataset is invalid.\n"
    )
    out.append("> **SYNTHETIC DATA NOTICE**\n>\n"
               f"> {FICTIONALITY_STATEMENT}\n>\n"
               f"> {PERFORMANCE_DISCLAIMER}\n")

    # legend
    out.append("\n## How to read this dictionary\n")
    out.append("### Field classification\n")
    out.append("| Role | Meaning |\n|---|---|")
    for role in ROLE_ORDER:
        out.append(f"| `{role}` | {_ROLE_MEANING[role]} |")
    out.append("\n### Prediction-time availability\n")
    out.append("| Value | Meaning |\n|---|---|")
    for k, v in AVAILABILITY_LEGEND.items():
        out.append(f"| `{k}` | {v} |")
    out.append("\n### Leakage risk\n")
    out.append("| Value | Meaning |\n|---|---|")
    for k, v in LEAKAGE_LEGEND.items():
        out.append(f"| `{k}` | {v} |")
    out.append(
        "\n**`Source timestamp`** is the column that carries the moment at which the field's "
        "content became known. The validator checks against the *data* that this timestamp is not "
        "later than the prediction point for every column in a feature set. That check is what "
        "makes the leakage boundary machine-verified rather than merely documented.\n"
    )
    out.append("\n### Nullability\n")
    out.append(NULLABILITY_NOTE + "\n")
    out.append("\n| Field | Null when |\n|---|---|")
    for name, why in STAGE_CONDITIONAL_COLUMNS.items():
        out.append(f"| `{name}` | {_md_escape(why)} |")
    out.append(
        "\n### Feature sets\n\n"
        "| Set | Population | Prediction point |\n|---|---|---|\n"
        f"| `primary` | applications that reached `application_submitted` | "
        f"`{prediction_point_column(FEATURE_SET_PRIMARY)}` |\n"
        f"| `decision` | applications that reached `admission_decision` | "
        f"`{prediction_point_column(FEATURE_SET_DECISION)}` |\n\n"
        "Feature sets are **allow-lists**. A column absent from a set is not a feature of that "
        "task.\n"
    )

    # entity index
    out.append("\n## Entity index\n")
    out.append("| Table | Row grain | Primary key | Pipeline role |\n|---|---|---|---|")
    for e in ENTITIES.values():
        out.append(f"| `{e.name}` | {e.grain} | `{e.primary_key}` | {e.role_in_pipeline} |")

    # per entity
    for e in ENTITIES.values():
        out.append(f"\n---\n\n## `{e.name}`\n")
        out.append(f"**Row grain.** {e.grain}\n")
        out.append(f"\n**Primary key.** `{e.primary_key}`\n")
        out.append(f"\n**Purpose.** {e.description}\n")
        out.append(f"\n**Column count.** {len(e.columns)}\n")
        out.append("\n" + _TABLE_HEADER)
        for c in e.columns:
            example = _md_escape(ex_of(c)) or "—"
            values = _fmt_categories(c.categories)
            req = "no (nullable)" if c.nullable else ("yes" if c.required else "no")
            feature = ", ".join(f"`{f}`" for f in c.feature_sets) if c.feature_sets else "—"
            example_cell = f"{example}<br>{values}" if values else example
            out.append(
                f"| `{c.name}` | `{c.dtype}` | {c.role} | {_md_escape(e.grain)} | {req} | "
                f"{c.availability} | `{c.source_ts_field or ''}` | {c.leakage} | {feature} | "
                f"{_md_escape(c.description)} | {_md_escape(c.generation_logic)} | "
                f"{example_cell} |"
            )

    # modelling view
    out.append(f"\n---\n\n## `applications_modelling_view` (denormalised, `data/processed/`)\n")
    out.append(f"{MV_DESCRIPTION}\n")
    out.append(
        f"\n**Row grain.** one row per application that reached `application_submitted`\n"
        f"\n**Column count.** {len(MV_COLUMNS)}\n"
    )
    out.append(
        "\n| Field | Source | Role | Required | Availability | Leakage risk | In `primary` | "
        "In `decision` | Description |\n|---|---|---|---|---|---|---|---|---|"
    )
    for m in MV_COLUMNS:
        src = f"`{m.source_entity}.{m.source_column}`"
        in_p = "yes" if m.in_primary else "no"
        in_d = "yes" if m.in_decision else "no"
        out.append(
            f"| `{m.name}` | {src} | {m.role} | no (nullable) | {m.availability} | {m.leakage} | "
            f"{in_p} | {in_d} | {_md_escape(m.description)} |"
        )

    # leakage section
    out.append("\n---\n\n## Leakage boundary\n")
    out.append("### SAFE prediction features — `primary` set\n")
    out.append("| Table | Field | Source timestamp |\n|---|---|---|")
    for ent, colname in feature_columns(FEATURE_SET_PRIMARY):
        col = ENTITIES[ent].col(colname)
        out.append(f"| `{ent}` | `{colname}` | `{col.source_ts_field or ''}` |")
    out.append("\n### POST-OUTCOME / TARGET fields — forbidden as primary features\n")
    out.append("| Table | Field | Role | Leakage |\n|---|---|---|---|")
    for ent, colname in post_outcome_columns():
        col = ENTITIES[ent].col(colname)
        out.append(f"| `{ent}` | `{colname}` | {col.role} | `{col.leakage}` |")
    out.append(
        "\n> `selection_score` is retained in the raw table **on purpose** (contract decision "
        "D-11). It is the most realistic leakage trap an admissions dataset contains: the "
        "institution's own merit score, computed at decision time, which does not exist at the "
        "prediction point. The validator fails the dataset if it appears in any feature set.\n"
    )

    out.append("\n---\n\n## Attribution semantics\n")
    out.append(
        "`acquisition_channel`, `acquisition_source` and `campaign_id` are **recorded "
        "associations, not causal effects**. Differences in conversion between channels arise "
        "because channels attract different applicant mixes. No causal, uplift or counterfactual "
        "claim is licensed by this dataset.\n"
    )
    out.append("\n---\n\n## PII boundary\n")
    out.append(
        "The dataset contains **no PII**: no names, emails, phone numbers, addresses, dates of "
        "birth or government identifiers. `applicant_id` and `application_id` are synthetic "
        "surrogate keys. Quasi-identifying attributes are coarse and synthetic (`region_id`, "
        "`gender_band`, `education_level`) and exist for segmentation only.\n"
    )
    out.append(f"\n---\n\n{FICTIONALITY_STATEMENT}\n\n> {PERFORMANCE_DISCLAIMER}\n")

    return "\n".join(out) + "\n"
