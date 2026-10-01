"""
AdmitFlow synthetic dataset generator.

Deterministic, configuration-driven generator for the fictional admission dataset described in
docs/admitflow_data_contract.md and registered in admitflow_schema.py.

Design principles enforced here:
  * NO deterministic rules. Every funnel transition is a Bernoulli draw from a logistic model of
    observable and latent factors, so the target is never a threshold of a feature.
  * Latent factors (ability, intent, financial constraint, competing offer) are only partially
    observed. This is what guarantees irreducible noise in `enrolled_flag`.
  * Timestamps come from process simulation, never from random assignment, and funnel milestones
    are strictly increasing (contract invariant F2).
  * No wall-clock time, no hostname and no machine-specific path enters the output.

Usage
-----
    python scripts/generate_dataset.py
    python scripts/generate_dataset.py --n-applications 30000 --seed 7
    python scripts/generate_dataset.py --emit-data-dictionary
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import admitflow_schema as S  # noqa: E402

EDUCATION_ORDER = ("higher_secondary", "diploma", "undergraduate", "other")


# ======================================================================================
# Configuration
# ======================================================================================


@dataclass
class GeneratorConfig:
    n_applications: int = 28_000
    n_cycles: int = 4
    start_cycle_year: int = 2022
    seed: int = 20240817
    min_history_weeks: int = 4
    min_applications_per_cell: int = 60
    max_applications_per_applicant: int = 3
    reuse_prob_same_cycle: float = 0.11
    reuse_prob_previous_cycle: float = 0.025
    forecast_horizons_weeks: Tuple[int, ...] = (1, 2, 4, 6)
    float_format: str = "%.6f"
    dataset_version: str = "1.0.0"

    def validate(self) -> None:
        if self.n_applications < 1000:
            raise ValueError("n_applications must be >= 1000")
        if self.n_cycles < 2:
            raise ValueError("n_cycles must be >= 2 (chronological split needs at least 2)")
        if not self.forecast_horizons_weeks:
            raise ValueError("at least one forecast horizon must be declared")
        if self.min_history_weeks + max(self.forecast_horizons_weeks) > 52:
            raise ValueError("min_history_weeks + max(forecast_horizons_weeks) must fit a year")


# ---- reference dimension content -------------------------------------------------------

REGIONS: Tuple[tuple, ...] = (
    ("REG-01", "Metro North", "metro", 180.0, 0.205),
    ("REG-02", "Metro East", "metro", 240.0, 0.178),
    ("REG-03", "Coastal South", "tier2", 640.0, 0.148),
    ("REG-04", "Highland West", "tier2", 815.0, 0.126),
    ("REG-05", "Central Plains", "tier3", 720.0, 0.118),
    ("REG-06", "Eastern Belt", "tier3", 690.0, 0.096),
    ("REG-07", "Desert Fringe", "rural_remote", 1080.0, 0.072),
    ("REG-08", "Hill Tracts", "rural_remote", 1240.0, 0.057),
)

PROGRAMMES: Tuple[dict, ...] = (
    dict(name="B.Sc. Data Science", code="BSC-DS", faculty="Faculty of Science", years=4,
         fee=185_000, seats=90, tier="high", review=7.5, demand=0.142, region="REG-01",
         score_shift=4.0, female_share=0.44,
         edu=(0.78, 0.06, 0.14, 0.02)),
    dict(name="B.Sc. Computer Science", code="BSC-CS", faculty="Faculty of Technology", years=4,
         fee=172_000, seats=120, tier="high", review=6.4, demand=0.151, region="REG-01",
         score_shift=3.0, female_share=0.36, edu=(0.74, 0.07, 0.17, 0.02)),
    dict(name="B.Sc. Information Technology", code="BSC-IT", faculty="Faculty of Technology",
         years=3, fee=158_000, seats=90, tier="medium", review=5.8, demand=0.121, region="REG-02",
         score_shift=2.0, female_share=0.38, edu=(0.70, 0.09, 0.19, 0.02)),
    dict(name="B.Sc. Mathematics", code="BSC-MA", faculty="Faculty of Science", years=3,
         fee=118_000, seats=60, tier="medium", review=7.1, demand=0.058, region="REG-01",
         score_shift=4.5, female_share=0.49, edu=(0.85, 0.04, 0.10, 0.01)),
    dict(name="B.Sc. Biotechnology", code="BSC-BT", faculty="Faculty of Science", years=3,
         fee=164_000, seats=60, tier="high", review=8.2, demand=0.066, region="REG-01",
         score_shift=3.5, female_share=0.61, edu=(0.80, 0.05, 0.13, 0.02)),
    dict(name="B.Sc. Physics", code="BSC-PH", faculty="Faculty of Science", years=3,
         fee=110_000, seats=45, tier="medium", review=7.6, demand=0.041, region="REG-01",
         score_shift=5.0, female_share=0.31, edu=(0.88, 0.03, 0.08, 0.01)),
    dict(name="B.Com (Hons.)", code="BCOM-H", faculty="Faculty of Commerce", years=3,
         fee=92_000, seats=150, tier="emerging", review=4.2, demand=0.138, region="REG-02",
         score_shift=-1.5, female_share=0.57, edu=(0.52, 0.18, 0.28, 0.02)),
    dict(name="BBA", code="BBA", faculty="Faculty of Management", years=3, fee=126_000,
         seats=120, tier="medium", review=4.0, demand=0.109, region="REG-02",
         score_shift=-2.0, female_share=0.47, edu=(0.50, 0.22, 0.26, 0.02)),
    dict(name="BCA", code="BCA", faculty="Faculty of Technology", years=3, fee=104_000,
         seats=90, tier="emerging", review=3.8, demand=0.094, region="REG-02",
         score_shift=-0.5, female_share=0.43, edu=(0.60, 0.18, 0.20, 0.02)),
    dict(name="B.A. Economics", code="BA-EC", faculty="Faculty of Humanities", years=3,
         fee=78_000, seats=60, tier="emerging", review=3.5, demand=0.052, region="REG-03",
         score_shift=-1.0, female_share=0.52, edu=(0.72, 0.08, 0.18, 0.02)),
    dict(name="B.Sc. Food Technology", code="BSC-FT", faculty="Faculty of Science", years=3,
         fee=132_000, seats=45, tier="emerging", review=6.0, demand=0.034, region="REG-05",
         score_shift=0.0, female_share=0.55, edu=(0.72, 0.10, 0.16, 0.02)),
    dict(name="B.Com (Taxation & Finance)", code="BCOM-TF", faculty="Faculty of Commerce",
         years=3, fee=86_000, seats=75, tier="emerging", review=3.9, demand=0.048, region="REG-03",
         score_shift=-0.5, female_share=0.45, edu=(0.55, 0.20, 0.23, 0.02)),
)

CAMPAIGN_TEMPLATES: Tuple[dict, ...] = (
    dict(channel="paid_search", suffix="PAID", label="Prospecting - Search",
         target_group="all_programmes"),
    dict(channel="paid_search", suffix="PAIDBR", label="Brand Defence - Search",
         target_group="science_and_technology"),
    dict(channel="social_media", suffix="SOC", label="Reach - Instagram & YouTube",
         target_group="open_house_followup"),
    dict(channel="social_media", suffix="SOCRT", label="Retargeting - Site Visitors",
         target_group="science_and_technology"),
    dict(channel="email_campaign", suffix="EML", label="Prospectus Nurture",
         target_group="commerce_and_management"),
    dict(channel="email_campaign", suffix="EMLoh", label="Open House Follow-up",
         target_group="all_programmes"),
    dict(channel="partner_agency", suffix="AGT", label="Partner Counsellor Push",
         target_group="all_programmes"),
    dict(channel="partner_agency", suffix="AGTN", label="NRI & Overseas Desk",
         target_group="science_and_technology"),
)

CHANNEL_MIX: Dict[int, Dict[str, float]] = {
    1: {"organic_search": 0.240, "paid_search": 0.170, "social_media": 0.140,
        "email_campaign": 0.090, "referral": 0.100, "direct": 0.090,
        "education_fair": 0.080, "partner_agency": 0.090},
    2: {"organic_search": 0.200, "paid_search": 0.150, "social_media": 0.120,
        "email_campaign": 0.120, "referral": 0.110, "direct": 0.100,
        "education_fair": 0.100, "partner_agency": 0.100},
}

CHANNEL_CYCLE_DRIFT: Dict[str, float] = {
    "organic_search": -0.055, "paid_search": 0.085, "social_media": 0.030,
    "email_campaign": 0.020, "referral": 0.045, "direct": 0.000,
    "education_fair": -0.020, "partner_agency": -0.030,
}

CHANNEL_START_EFFECT = {"organic_search": 0.25, "paid_search": -0.15, "social_media": -0.30,
                        "email_campaign": 0.05, "referral": 0.45, "direct": 0.15,
                        "education_fair": -0.10, "partner_agency": -0.20}
CHANNEL_SUBMIT_EFFECT = {"organic_search": 0.15, "paid_search": -0.10, "social_media": -0.25,
                         "email_campaign": 0.10, "referral": 0.35, "direct": 0.20,
                         "education_fair": 0.05, "partner_agency": -0.05}
CHANNEL_VERIFY_EFFECT = {"organic_search": 0.00, "paid_search": -0.05, "social_media": -0.30,
                         "email_campaign": 0.00, "referral": 0.10, "direct": 0.00,
                         "education_fair": 0.05, "partner_agency": -0.15}
CHANNEL_ENROL_EFFECT = {"organic_search": 0.15, "paid_search": -0.10, "social_media": -0.25,
                        "email_campaign": 0.05, "referral": 0.30, "direct": 0.10,
                        "education_fair": 0.05, "partner_agency": 0.15}
CHANNEL_TOUCHPOINT_RATE = {"organic_search": 1.9, "paid_search": 2.9, "social_media": 2.4,
                           "email_campaign": 3.1, "referral": 2.2, "direct": 1.2,
                           "education_fair": 1.6, "partner_agency": 3.4}
CHANNEL_REGION_TILT: Dict[str, np.ndarray] = {
    "organic_search": np.array([1.15, 1.10, 1.00, 0.95, 0.90, 0.90, 0.85, 0.85]),
    "paid_search": np.array([1.45, 1.35, 1.00, 0.85, 0.80, 0.80, 0.70, 0.70]),
    "social_media": np.array([1.10, 1.00, 1.05, 0.95, 0.90, 0.95, 0.90, 0.90]),
    "email_campaign": np.array([1.05, 1.05, 1.05, 1.00, 0.95, 0.95, 0.90, 0.90]),
    "referral": np.array([0.85, 0.90, 1.05, 1.05, 1.10, 1.10, 1.15, 1.10]),
    "direct": np.array([1.05, 1.05, 1.00, 1.00, 1.00, 1.00, 0.95, 0.95]),
    "education_fair": np.array([0.80, 0.85, 1.05, 1.10, 1.15, 1.15, 1.15, 1.05]),
    "partner_agency": np.array([1.30, 1.30, 1.10, 1.05, 1.00, 0.95, 0.85, 0.85]),
}
CHANNEL_EDUCATION_TILT: Dict[str, np.ndarray] = {
    "organic_search": np.array([1.00, 1.10, 1.00, 0.90]),
    "paid_search": np.array([1.10, 1.05, 0.95, 0.90]),
    "social_media": np.array([1.20, 0.90, 0.90, 0.90]),
    "email_campaign": np.array([1.05, 1.05, 1.00, 0.90]),
    "referral": np.array([0.95, 1.00, 1.10, 0.95]),
    "direct": np.array([0.95, 1.00, 1.10, 0.95]),
    "education_fair": np.array([1.30, 0.85, 0.80, 0.85]),
    "partner_agency": np.array([0.90, 1.10, 1.10, 0.95]),
}

TIER_ADMIT_LOGIT = {"emerging": 0.75, "medium": 0.20, "high": -0.30}
TIER_CUTOFF = {"emerging": 52.0, "medium": 59.0, "high": 65.0}
EDUCATION_ADMIT_EFFECT = {"higher_secondary": 0.12, "diploma": -0.10, "undergraduate": 0.04,
                          "other": -0.30}

DROPOFF_REASONS_BY_STAGE: Dict[str, Tuple[str, ...]] = {
    "prospect": ("no_response", "browsed_only", "enquiry_closed_unqualified"),
    "application_started": ("form_abandoned", "deadline_missed", "requirements_unclear"),
    "application_submitted": ("incomplete_documents", "ineligible_qualification",
                              "verification_timeout"),
    "application_verified": ("withdrawn_by_applicant", "accepted_elsewhere_withdrawn"),
    "admission_decision": ("below_merit_cutoff", "eligibility_criteria_failed",
                           "capacity_exhausted"),
    "admitted": ("offer_not_accepted", "chose_other_institution", "financial_constraint",
                 "offer_deadline_lapsed"),
}

# Real funnel exits are not uniform: most rejections are merit-driven, most prospect losses are
# silence. The weights below are the reason mix the generator is expected to reproduce.
DROPOFF_REASON_WEIGHTS: Dict[str, Dict[str, float]] = {
    "prospect": {"no_response": 0.50, "browsed_only": 0.34, "enquiry_closed_unqualified": 0.16},
    "application_started": {"form_abandoned": 0.46, "deadline_missed": 0.36,
                            "requirements_unclear": 0.18},
    "application_submitted": {"incomplete_documents": 0.52, "ineligible_qualification": 0.36,
                              "verification_timeout": 0.12},
    "application_verified": {"withdrawn_by_applicant": 0.62,
                              "accepted_elsewhere_withdrawn": 0.38},
    "admission_decision": {"below_merit_cutoff": 0.71, "eligibility_criteria_failed": 0.19,
                           "capacity_exhausted": 0.10},
    "admitted": {"offer_not_accepted": 0.27, "chose_other_institution": 0.26,
                 "financial_constraint": 0.19, "offer_deadline_lapsed": 0.28},
}

APPLICANT_COLUMNS = (
    "application_id", "applicant_id", "programme_id", "cycle_id", "campaign_id",
    "acquisition_channel", "acquisition_source", "first_touch_date", "touchpoints_count",
    "is_multi_touch", "is_referral_alumni", "intake_round", "academic_score_pct",
    "academic_score_band", "doc_completeness_score", "fee_scholarship_applied", "inquiry_ts",
    "application_started_ts", "application_submitted_ts", "prediction_ts", "prediction_stage",
    "is_repeat_applicant_at_prediction", "days_inquiry_to_start", "days_start_to_submit",
    "days_inquiry_to_submit", "days_to_round_close_at_start", "week_of_cycle_at_submission",
    "month_of_submission", "pre_sub_session_count", "pre_sub_active_days",
    "pre_sub_total_minutes", "pre_sub_doc_uploads", "pre_sub_form_fields_completed",
    "pre_sub_return_visits", "stage_reached", "stage_reached_order", "dropoff_stage",
    "dropoff_reason", "doc_query_raised", "doc_query_count", "doc_verification_status",
    "application_verified_ts", "admission_decision_ts", "admitted_ts", "enrolled_ts",
    "days_submitted_to_verified", "days_verified_to_decision", "days_decision_to_enrolled",
    "decision_type", "selection_score", "offer_letter_issued", "offer_deadline",
    "scholarship_offered", "scholarship_amount_inr", "withdrawn_flag", "withdrawn_date",
    "admitted_flag", "enrolled_given_admitted_flag", "enrolled_flag",
)


# ======================================================================================
# Small utilities
# ======================================================================================


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def clip(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else (hi if x > hi else x)


def iso(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%S")


def iso_d(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def parse_iso(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")


def band_score(score: float) -> str:
    if score < 60:
        return "lt_60"
    if score < 70:
        return "60_69"
    if score < 80:
        return "70_79"
    if score < 90:
        return "80_89"
    return "90_plus"


def largest_remainder(weights: np.ndarray, total: int) -> np.ndarray:
    w = np.asarray(weights, dtype=float)
    w = w / w.sum()
    raw = w * total
    base = np.floor(raw).astype(int)
    remainder = total - int(base.sum())
    if remainder > 0:
        frac = raw - base
        order = np.lexsort((np.arange(len(w)), -frac))
        base[order[:remainder]] += 1
    return base


def choose(rng: np.random.Generator, n: int, p: Sequence[float]) -> int:
    cdf = np.cumsum(np.asarray(p, dtype=float))
    cdf = cdf / cdf[-1]
    return int(np.searchsorted(cdf, rng.random(), side="right"))


def rnd_hour(rng: np.random.Generator) -> int:
    h = choose(rng, 16, [0.02, 0.02, 0.02, 0.02, 0.03, 0.05, 0.08, 0.09, 0.10, 0.11,
                         0.11, 0.10, 0.09, 0.08, 0.06, 0.05])
    return 8 + h


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


# ======================================================================================
# Dimension builders
# ======================================================================================


def build_dim_funnel_stage() -> pd.DataFrame:
    return pd.DataFrame([
        dict(stage_order=s["stage_order"], stage_code=s["stage_code"], stage_name=s["stage_name"],
             stage_kind=s["stage_kind"], allows_reentry=bool(s["allows_reentry"]),
             requires_all_prior_stages=bool(s["requires_all_prior_stages"]),
             stage_description=s["description"])
        for s in S.FUNNEL_STAGES
    ])


def build_dim_region(rng: np.random.Generator) -> pd.DataFrame:
    rows = [dict(region_id=rid, region_name=name, region_type=rtype,
                 mean_distance_km_to_campus=round(float(dist * (1 + rng.normal(0, 0.06))), 3),
                 region_inquiry_weight=round(float(share * (1 + rng.normal(0, 0.04))), 6))
            for rid, name, rtype, dist, share in REGIONS]
    df = pd.DataFrame(rows)
    df["region_inquiry_weight"] = (df["region_inquiry_weight"]
                                   / df["region_inquiry_weight"].sum()).round(6)
    return df


def build_dim_programme(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for i, p in enumerate(PROGRAMMES, start=1):
        rows.append(dict(
            programme_id=f"PGM-{i:02d}",
            programme_name=p["name"],
            programme_code=p["code"],
            faculty=p["faculty"],
            award_level="UG",
            duration_years=int(p["years"]),
            annual_fee_inr=int(round(p["fee"] * math.exp(rng.normal(0, 0.10)) / 500) * 500),
            base_seat_capacity=int(p["seats"]),
            selectivity_tier=p["tier"],
            review_duration_days=round(float(p["review"]) * (1 + rng.normal(0, 0.05)), 3),
            demand_weight=round(float(p["demand"]) * (1 + rng.normal(0, 0.05)), 6),
            campus_region_id=p["region"],
        ))
    df = pd.DataFrame(rows)
    df["demand_weight"] = (df["demand_weight"] / df["demand_weight"].sum()).round(6)
    return df


def cycle_calendar(start_year: int, n_cycles: int) -> List[dict]:
    out = []
    for i in range(n_cycles):
        y = start_year + i
        out.append(dict(
            cycle_id=f"CYC-{y}", academic_year_label=f"AY{y}-{(y + 1) % 100:02d}",
            cycle_year=y, cycle_index=i,
            intake1_application_open=date(y, 6, 1),
            intake1_application_close=date(y, 10, 15),
            intake1_decision_start=date(y, 11, 20),
            intake1_decision_end=date(y, 11, 27),
            intake1_offer_deadline=date(y + 1, 1, 10),
            intake1_enrolment_end=date(y + 1, 2, 5),
            intake2_application_open=date(y, 10, 16),
            intake2_application_close=date(y, 12, 20),
            intake2_decision_start=date(y + 1, 1, 15),
            intake2_decision_end=date(y + 1, 1, 22),
            intake2_offer_deadline=date(y + 1, 2, 25),
            intake2_enrolment_end=date(y + 1, 3, 20),
        ))
    return out


def build_cycles_table(cycles: List[dict], programs: pd.DataFrame) -> pd.DataFrame:
    total_seats = int(programs["base_seat_capacity"].sum())
    rows = []
    for c in cycles:
        start, end = c["intake1_application_open"], c["intake2_enrolment_end"]
        rows.append(dict(
            cycle_id=c["cycle_id"], academic_year_label=c["academic_year_label"],
            cycle_start_date=iso_d(start), cycle_end_date=iso_d(end),
            intake1_application_open=iso_d(c["intake1_application_open"]),
            intake1_application_close=iso_d(c["intake1_application_close"]),
            intake1_decision_start=iso_d(c["intake1_decision_start"]),
            intake1_decision_end=iso_d(c["intake1_decision_end"]),
            intake1_offer_deadline=iso_d(c["intake1_offer_deadline"]),
            intake1_enrolment_end=iso_d(c["intake1_enrolment_end"]),
            intake2_application_open=iso_d(c["intake2_application_open"]),
            intake2_application_close=iso_d(c["intake2_application_close"]),
            intake2_decision_start=iso_d(c["intake2_decision_start"]),
            intake2_decision_end=iso_d(c["intake2_decision_end"]),
            intake2_offer_deadline=iso_d(c["intake2_offer_deadline"]),
            intake2_enrolment_end=iso_d(c["intake2_enrolment_end"]),
            verification_end_date=iso_d(c["intake2_application_close"] + timedelta(days=21)),
            total_weeks=int((monday_of(end) - monday_of(start)).days // 7 + 1),
            is_finalised=True, total_seats_offers=total_seats,
        ))
    return pd.DataFrame(rows)


def build_dim_campaign(rng: np.random.Generator, cycles: List[dict]) -> pd.DataFrame:
    rows = []
    for c in cycles:
        y = c["cycle_year"]
        for t in CAMPAIGN_TEMPLATES:
            start = c["intake1_application_open"] + timedelta(days=int(rng.integers(0, 21)))
            end = c["intake2_application_close"] - timedelta(days=int(rng.integers(0, 21)))
            if end <= start:
                end = start + timedelta(days=30)
            rows.append(dict(
                campaign_id=f"CMP-{y}-{t['suffix']}",
                campaign_name=f"{c['academic_year_label']} {t['label']}",
                channel=t["channel"], cycle_id=c["cycle_id"],
                start_date=iso_d(start), end_date=iso_d(end),
                planned_budget_inr=int(round(math.exp(rng.normal(13.4, 0.55)) / 5000) * 5000),
                target_group=t["target_group"], is_active=True,
            ))
    return pd.DataFrame(rows).sort_values("campaign_id").reset_index(drop=True)


def allocate_cells(programs: pd.DataFrame, cycles: List[dict], n_applications: int,
                   min_per_cell: int) -> Dict[Tuple[str, str], int]:
    pids = programs["programme_id"].tolist()
    demands = programs["demand_weight"].to_numpy()
    keys: List[Tuple[str, str]] = []
    weights: List[float] = []
    for c in cycles:
        for i, pid in enumerate(pids):
            sign = 1.0 if (i + c["cycle_index"]) % 2 == 0 else -1.0
            drift = 1.0 + sign * 0.055 * (c["cycle_index"] + 1) * 0.5
            weights.append(float(demands[i]) * drift)
            keys.append((pid, c["cycle_id"]))
    counts = largest_remainder(np.array(weights), n_applications).astype(int)

    while True:
        low = [i for i in range(len(counts)) if counts[i] < min_per_cell]
        if not low:
            break
        deficit = 0
        for i in low:
            deficit += min_per_cell - counts[i]
            counts[i] = min_per_cell
        donors = sorted((i for i in range(len(counts)) if counts[i] > min_per_cell + 30),
                        key=lambda i: (-counts[i], i))
        for i in donors:
            take = min(deficit, int(counts[i]) - min_per_cell - 30)
            counts[i] -= take
            deficit -= take
            if deficit == 0:
                break
        if deficit > 0:
            break
    return {k: int(v) for k, v in zip(keys, counts)}


def _split_hint(idx: int, n: int) -> str:
    """Delegate to the schema so the generator and the validator cannot drift apart."""
    return S.split_hint(idx, n)


# ======================================================================================
# Simulation
# ======================================================================================


@dataclass
class SimState:
    applications: List[dict]
    engagement: List[dict]
    applicants: Dict[str, dict]
    counters: Dict[str, int]
    n_by_cell: Dict[Tuple[str, str], int]


def _next_id(counters: Dict[str, int], prefix: str, width: int) -> str:
    counters[prefix] = counters.get(prefix, 0) + 1
    return f"{prefix}{counters[prefix]:0{width}d}"


def _pick_reason(rng: np.random.Generator, stage: str) -> str:
    opts = DROPOFF_REASONS_BY_STAGE[stage]
    w = [DROPOFF_REASON_WEIGHTS[stage][o] for o in opts]
    return opts[choose(rng, len(opts), w)]


def _blank_app(st: SimState, aid: str, pid: str, cid: str, camp_id: Optional[str], channel: str,
               source: str, ft_date: date, touchpoints: int, is_multi: bool, is_alumni: bool,
               rnd: int, inquiry_ts: datetime) -> dict:
    app_id = _next_id(st.counters, "APP", 7)
    rec = {k: None for k in APPLICANT_COLUMNS}
    rec.update(
        application_id=app_id, applicant_id=aid, programme_id=pid, cycle_id=cid,
        campaign_id=camp_id, acquisition_channel=channel, acquisition_source=source,
        first_touch_date=iso_d(ft_date), touchpoints_count=int(touchpoints),
        is_multi_touch=bool(is_multi), is_referral_alumni=bool(is_alumni), intake_round=int(rnd),
        doc_query_raised=False, doc_query_count=0, doc_verification_status="not_initiated",
        offer_letter_issued=False, scholarship_offered=False, scholarship_amount_inr=0,
        withdrawn_flag=False, admitted_flag=0, enrolled_flag=0, stage_reached="prospect",
        stage_reached_order=1,
        _inq_ts=inquiry_ts, _start_ts=None, _submit_dt=None, _eng=None, _window=None,
        _z_ability=0.0, _z_intent=0.0, _z_constraint=0.0, _competing=0.0,
    )
    rec["inquiry_ts"] = iso(inquiry_ts)
    st.applicants[aid]["app_ids"].append(app_id)
    return rec


def simulate(cfg: GeneratorConfig, programs: pd.DataFrame, regions: pd.DataFrame,
             cycles: List[dict], campaigns: pd.DataFrame,
             min_per_cell: int) -> SimState:
    rng = np.random.default_rng(np.random.SeedSequence(cfg.seed).spawn(4)[0])

    prog_by_id: Dict[str, dict] = {}
    for row in programs.to_dict("records"):
        meta = next(x for x in PROGRAMMES if x["code"] == row["programme_code"])
        prog_by_id[row["programme_id"]] = {**row, "score_shift": meta["score_shift"],
                                           "female_share": meta["female_share"],
                                           "edu": meta["edu"]}
    region_ids = regions["region_id"].tolist()
    base_region_w = regions["region_inquiry_weight"].to_numpy()

    cells = allocate_cells(programs, cycles, cfg.n_applications, min_per_cell)

    camp_index: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    for c in campaigns.to_dict("records"):
        camp_index[(c["cycle_id"], c["channel"])].append(c)

    merit: Dict[Tuple[str, str], dict] = {}
    for (pid, cid), n in cells.items():
        c = next(x for x in cycles if x["cycle_id"] == cid)
        p = prog_by_id[pid]
        crowding = n / (p["base_seat_capacity"] * 3.0)
        merit[(pid, cid)] = dict(
            crowding=crowding,
            cutoff=TIER_CUTOFF[p["selectivity_tier"]] + 0.45 * c["cycle_index"],
            base_logit=TIER_ADMIT_LOGIT[p["selectivity_tier"]] - 0.06 * c["cycle_index"]
            - 0.62 * math.log(max(crowding, 0.15)),
            decision_offset_days=int(rng.integers(0, 11)),
            score_shift=p["score_shift"] * (1.0 + 0.05 * c["cycle_index"]),
        )

    st = SimState(applications=[], engagement=[], applicants={}, counters={}, n_by_cell=cells)
    prev_cycle_pool: List[str] = []

    for cy in sorted(cycles, key=lambda c: c["cycle_index"]):
        cid, cidx = cy["cycle_id"], cy["cycle_index"]
        cycle_pool: List[str] = []
        taken: set = set()
        ver_end = cy["intake2_application_close"] + timedelta(days=21)

        for pid in sorted(prog_by_id):
            p = prog_by_id[pid]
            m = merit[(pid, cid)]
            edu_mix = np.asarray(p["edu"], dtype=float)

            for _ in range(cells[(pid, cid)]):
                # ---- applicant resolution ------------------------------------------------
                aid = None
                r = float(rng.random())
                if prev_cycle_pool and r < cfg.reuse_prob_previous_cycle:
                    cand = prev_cycle_pool[int(rng.integers(0, len(prev_cycle_pool)))]
                    if (cand, pid) not in taken and \
                            len(st.applicants[cand]["app_ids"]) < cfg.max_applications_per_applicant:
                        aid = cand
                if aid is None and cycle_pool and r < cfg.reuse_prob_same_cycle:
                    cand = cycle_pool[int(rng.integers(0, len(cycle_pool)))]
                    if (cand, pid) not in taken and \
                            len(st.applicants[cand]["app_ids"]) < cfg.max_applications_per_applicant:
                        aid = cand
                if aid is None:
                    aid = _next_id(st.counters, "APL", 7)
                    st.applicants[aid] = dict(applicant_id=aid, region_id=None, gender_band=None,
                                              education_level=None, first_inquiry_date=None,
                                              app_ids=[])
                    cycle_pool.append(aid)
                ap = st.applicants[aid]

                # ---- acquisition -------------------------------------------------------
                rnd = 1 if rng.random() < 0.42 else 2
                mix = {ch: v * (1.0 + CHANNEL_CYCLE_DRIFT[ch] * cidx)
                       for ch, v in CHANNEL_MIX[rnd].items()}
                chans = list(mix.keys())
                channel = chans[choose(rng, len(chans), [mix[c] for c in chans])]
                srcs = S.ACQUISITION_SOURCE_EXAMPLES[channel]
                source = srcs[int(rng.integers(0, len(srcs)))]

                # ---- applicant attributes (frozen on creation) -------------------------
                if ap["region_id"] is None:
                    ap["region_id"] = region_ids[
                        choose(rng, len(region_ids), base_region_w * CHANNEL_REGION_TILT[channel])]
                    ap["education_level"] = EDUCATION_ORDER[
                        choose(rng, 4, edu_mix * CHANNEL_EDUCATION_TILT[channel])]
                    g = float(rng.random())
                    ap["gender_band"] = ("female" if g < p["female_share"]
                                         else ("male" if g < 0.945
                                               else "other_or_prefer_not_to_say"))

                # ---- latent factors ----------------------------------------------------
                z_ability = float(rng.normal(0, 1))
                z_intent = float(rng.normal(0, 1))
                z_constraint = (float(rng.normal(0, 1))
                                + (0.35 if ap["education_level"] == "other" else 0.0)
                                + (0.30 if p["annual_fee_inr"] > 150_000 else 0.0))
                competing = float(rng.normal(0, 1))

                # ---- intake round, inquiry timestamp ------------------------------------
                if rnd == 1:
                    open_d, close_d = cy["intake1_application_open"], cy["intake1_application_close"]
                    dec_start = cy["intake1_decision_start"]
                    offer_deadline_base = cy["intake1_offer_deadline"]
                    enrol_end = cy["intake1_enrolment_end"]
                else:
                    open_d, close_d = cy["intake2_application_open"], cy["intake2_application_close"]
                    dec_start = cy["intake2_decision_start"]
                    offer_deadline_base = cy["intake2_offer_deadline"]
                    enrol_end = cy["intake2_enrolment_end"]
                window = (close_d - open_d).days
                u = 0.72 * float(rng.beta(1.7, 2.3)) + 0.28 * float(rng.beta(3.0, 1.4))
                inq_date = open_d + timedelta(days=int(min(window - 1, max(0.0, u * window))))
                inquiry_ts = datetime.combine(inq_date, datetime.min.time()) + \
                    timedelta(hours=rnd_hour(rng), minutes=int(rng.integers(0, 60)))
                close_ts = datetime.combine(close_d, datetime.min.time()) + timedelta(hours=23)
                if ap["first_inquiry_date"] is None or inq_date < ap["first_inquiry_date"]:
                    ap["first_inquiry_date"] = inq_date

                lead_lag = int(min(180, round(float(rng.gamma(1.2, 3.0)))))
                ft_date = max(cy["intake1_application_open"], inq_date - timedelta(days=lead_lag))
                touchpoints = int(min(12, 1 + rng.poisson(CHANNEL_TOUCHPOINT_RATE[channel])))
                is_alumni = bool(channel == "referral" and rng.random() < 0.28)
                camp_id = None
                if channel in S.CAMPAIGN_CHANNELS and rng.random() < 0.88:
                    cands = [c for c in camp_index.get((cid, channel), [])
                             if c["start_date"] <= iso_d(ft_date) <= c["end_date"]]
                    if cands:
                        camp_id = cands[int(rng.integers(0, len(cands)))]["campaign_id"]

                rec = _blank_app(st, aid, pid, cid, camp_id, channel, source, ft_date,
                                 touchpoints, touchpoints > 1, is_alumni, rnd, inquiry_ts)

                # ---- stage 1 -> 2 ------------------------------------------------------
                logit_start = (0.28 + 0.62 * z_intent + CHANNEL_START_EFFECT[channel]
                               + 0.14 * (ap["education_level"] == "undergraduate")
                               + 0.10 * (ap["region_id"] in ("REG-01", "REG-02"))
                               - 0.22 * max(0.0, u - 0.75) * 4.0)
                started = bool(rng.random() < sigmoid(logit_start))

                if started:
                    start_lag = max(0, int(round(float(rng.gamma(1.4, 2.2)))))
                    start_ts = inquiry_ts + timedelta(days=start_lag,
                                                       hours=int(rng.integers(0, 10)))
                    if start_ts > close_ts:
                        start_ts = close_ts - timedelta(hours=int(rng.integers(1, 20)))
                    if start_ts <= inquiry_ts:
                        start_ts = inquiry_ts + timedelta(hours=int(rng.integers(3, 40)))
                    start_date = start_ts.date()
                    days_avail = max(0, (close_d - start_date).days)
                    rec["_start_ts"] = start_ts
                    rec["application_started_ts"] = iso(start_ts)
                    rec["days_inquiry_to_start"] = (start_date - inq_date).days
                    rec["days_to_round_close_at_start"] = days_avail

                    eng_mu = 1.05 + 0.42 * z_intent + 0.18 * CHANNEL_START_EFFECT[channel]
                    n_days = int(min(14, max(1, rng.poisson(
                        max(0.10, 3.30 + 1.35 * z_intent)))))
                    total_min = float(np.clip(rng.gamma(5.0 * math.exp(eng_mu - 1.0), 11.0),
                                              4.0, 900.0))
                    eng_index = clip(math.log1p(n_days * total_min) / 3.0, 0.0, 3.0)

                    # ---- stage 2 -> 3 ------------------------------------------------
                    logit_submit = (0.35 + 0.58 * z_intent + 0.50 * eng_index
                                    + CHANNEL_SUBMIT_EFFECT[channel]
                                    + 0.30 * (ap["education_level"] == "undergraduate")
                                    + 0.18 * (ap["education_level"] == "diploma")
                                    - 0.020 * max(0, days_avail - 60)
                                    - 0.55 * max(0, 14 - days_avail))
                    if days_avail == 0:
                        logit_submit = -6.0
                    submitted = bool(rng.random() < sigmoid(logit_submit))

                    if submitted:
                        sub_days = min(max(0, int(round(float(rng.gamma(1.8, 1.9))))),
                                       days_avail)
                        submit_ts = start_ts + timedelta(days=sub_days,
                                                          hours=int(rng.integers(1, 14)))
                        if submit_ts <= start_ts:
                            submit_ts = start_ts + timedelta(hours=int(rng.integers(1, 9)))
                        if submit_ts > close_ts:
                            submit_ts = close_ts - timedelta(minutes=int(rng.integers(30, 600)))
                        submitted = submit_ts > start_ts

                    if submitted:
                        score = round(clip(58.0 + m["score_shift"] + 9.0 * z_ability
                                           + 5.0 * float(rng.normal(0, 1)), 40.0, 99.0), 1)
                        doc = round(clip(
                            sigmoid(1.35 + 1.05 * z_ability + 0.75 * z_intent
                                    - 0.80 * math.log1p(1.0 / max(1, days_avail))
                                    ) + float(rng.normal(0, 0.08)), 0.15, 1.0), 4)
                        fee_app = bool(rng.random() < sigmoid(
                            -1.55 + 0.45 * (ap["education_level"] == "diploma")
                            + 0.35 * (ap["education_level"] == "other")
                            + 0.30 * (ap["region_id"] in ("REG-07", "REG-08"))
                            - 0.45 * (p["annual_fee_inr"] > 150_000) + 0.45 * z_constraint))
                        sub_date = submit_ts.date()
                        rec.update(
                            application_submitted_ts=iso(submit_ts),
                            prediction_ts=iso(submit_ts), prediction_stage="application_submitted",
                            academic_score_pct=score, academic_score_band=band_score(score),
                            doc_completeness_score=doc, fee_scholarship_applied=fee_app,
                            days_start_to_submit=(sub_date - start_date).days,
                            days_inquiry_to_submit=(sub_date - inq_date).days,
                            week_of_cycle_at_submission=int(
                                (sub_date - cy["intake1_application_open"]).days // 7),
                            month_of_submission=sub_date.month,
                            _submit_dt=submit_ts, _z_ability=z_ability, _z_intent=z_intent,
                            _z_constraint=z_constraint, _competing=competing,
                            _eng=(n_days, total_min),
                            _window=(start_date, sub_date),
                        )
                        taken.add((aid, pid))
                        _simulate_post_submission(st, rec, p, cy, rnd, m, dec_start,
                                                  offer_deadline_base, enrol_end, ver_end, rng)
                        st.applications.append(rec)
                        continue
                    rec["_eng"] = (n_days, total_min)
                    rec["_window"] = (start_date,
                                      min(close_d, start_date + timedelta(days=10)))
                    rec["dropoff_stage"] = "application_started"
                    rec["dropoff_reason"] = _pick_reason(rng, "application_started")
                else:
                    rec["dropoff_stage"] = "prospect"
                    rec["dropoff_reason"] = _pick_reason(rng, "prospect")

                rec["stage_reached"] = rec["dropoff_stage"]
                rec["stage_reached_order"] = S.STAGE_ORDER[rec["stage_reached"]]
                st.applications.append(rec)

        prev_cycle_pool = cycle_pool

    _realise_engagement(st, rng)
    _post_pass_repeat_flag(st)
    _build_events(st)
    return st


def _simulate_post_submission(st: SimState, rec: dict, p: dict, cy: dict, rnd: int, m: dict,
                              dec_start: date, offer_deadline_base: date, enrol_end: date,
                              ver_end: date, rng: np.random.Generator) -> None:
    submit_ts = rec["_submit_dt"]
    ap = st.applicants[rec["applicant_id"]]
    channel = rec["acquisition_channel"]
    score = rec["academic_score_pct"]
    doc = rec["doc_completeness_score"]
    z_ability = rec["_z_ability"]
    z_intent = rec["_z_intent"]

    # ---- stage 3 -> 4 : submitted -> verified -----------------------------------------
    # Documentation clarification request: a low-probability, completeness-driven event.
    query_raised = bool(rng.random() < sigmoid(0.75 - 3.10 * doc
                                              - 0.45 * (ap["education_level"] == "other")
                                              + CHANNEL_VERIFY_EFFECT[channel]))
    query_count = 0
    verify_delay = 0
    # Eligibility screen: a low-probability failure that gets MORE likely with a weak
    # document set, a weaker prior qualification and a lower qualifying score. It is a
    # probabilistic screen, not a threshold rule, so it is never perfectly predictable.
    p_ineligible = sigmoid(-3.40 + 0.95 * (ap["education_level"] == "other")
                           + 0.55 * (ap["education_level"] == "diploma")
                           - 1.80 * (doc - 0.80) - 0.030 * (score - 60.0))
    ineligible = bool((ap["education_level"] == "other" and score < 50.0)
                      or rng.random() < p_ineligible)

    if ineligible:
        verified = False
        rec["doc_verification_status"] = "rejected_ineligible"
        rec["dropoff_stage"] = "application_submitted"
        rec["dropoff_reason"] = "ineligible_qualification"
    elif query_raised:
        query_count = int(1 + rng.poisson(0.4))
        verify_delay = int(4 + round(float(rng.gamma(1.6, 3.2))))
        p_correction = clip(0.44 + 0.85 * (doc - 0.70) + 0.20 * z_intent, 0.10, 0.94)
        verified = bool(rng.random() < p_correction)
        rec["doc_verification_status"] = "verified" if verified else "returned_for_correction"
        if not verified:
            rec["dropoff_stage"] = "application_submitted"
            rec["dropoff_reason"] = "incomplete_documents"
    else:
        verified = bool(rng.random() < sigmoid(3.0 - 1.2 * (1.0 - doc)))
        rec["doc_verification_status"] = "verified" if verified else "returned_for_correction"
        if not verified:
            rec["dropoff_stage"] = "application_submitted"
            rec["dropoff_reason"] = "incomplete_documents"
    rec["doc_query_raised"] = bool(query_raised)
    rec["doc_query_count"] = int(query_count)

    vts = None
    if verified:
        base_lag = max(1.0, p["review_duration_days"] * math.exp(rng.normal(0, 0.32)))
        vts = submit_ts + timedelta(days=float(base_lag) + verify_delay,
                                    hours=int(rng.integers(1, 12)))
        hard = datetime.combine(ver_end, datetime.min.time()) + timedelta(hours=23, minutes=59)
        if vts > hard:
            vts = hard - timedelta(minutes=int(rng.integers(30, 500)))
        if vts <= submit_ts:
            verified = False
            rec["doc_verification_status"] = "returned_for_correction"
            rec["dropoff_stage"] = "application_submitted"
            rec["dropoff_reason"] = "verification_timeout"
    if not verified:
        rec["stage_reached"] = "application_submitted"
        rec["stage_reached_order"] = S.STAGE_ORDER["application_submitted"]
        return

    rec["application_verified_ts"] = iso(vts)
    rec["days_submitted_to_verified"] = (vts.date() - submit_ts.date()).days

    # ---- withdrawal between verification and the decision ------------------------------
    if rng.random() < 0.018:
        wd = vts + timedelta(days=int(1 + rng.integers(0, 20)))
        if wd.date() > dec_start:
            wd = datetime.combine(dec_start, datetime.min.time()) - timedelta(days=1)
        if wd <= vts:
            wd = vts + timedelta(days=1)
        rec["withdrawn_flag"] = True
        rec["withdrawn_date"] = iso_d(wd.date())
        rec["dropoff_stage"] = "application_verified"
        rec["dropoff_reason"] = _pick_reason(rng, "application_verified")
        rec["stage_reached"] = "application_verified"
        rec["stage_reached_order"] = S.STAGE_ORDER["application_verified"]
        return

    # ---- stage 4 -> 5 / 6 : decision and admission --------------------------------------
    dts = datetime.combine(dec_start, datetime.min.time()) + \
        timedelta(days=int(m["decision_offset_days"]) + int(rng.integers(0, 3)),
                   hours=int(rng.integers(9, 18)), minutes=int(rng.integers(0, 60)))
    if dts <= vts:
        dts = vts + timedelta(days=1, hours=6)
    dts_date = dts.date()

    margin = (score - m["cutoff"]) / 10.0
    logit_admit = (m["base_logit"] + 1.15 * margin + 0.45 * z_ability + 0.40 * (doc - 0.75)
                   + EDUCATION_ADMIT_EFFECT[ap["education_level"]]
                   + 0.18 * (ap["region_id"] in ("REG-01", "REG-02"))
                   - 0.25 * (ap["education_level"] == "other"))
    admit = bool(rng.random() < sigmoid(logit_admit))

    rec["admission_decision_ts"] = iso(dts)
    rec["days_verified_to_decision"] = (dts_date - vts.date()).days
    rec["selection_score"] = round(clip(
        0.55 * score + 12.0 * z_ability + 6.0
        + {"higher_secondary": 1.5, "diploma": -1.0, "undergraduate": 0.5,
           "other": -4.0}[ap["education_level"]]
        + 0.30 * (rec["month_of_submission"] - 8), 0.0, 100.0), 2)

    if not admit:
        rec["decision_type"] = "reject"
        rec["dropoff_stage"] = "admission_decision"
        rec["dropoff_reason"] = _pick_reason(rng, "admission_decision")
        rec["stage_reached"] = "admission_decision"
        rec["stage_reached_order"] = S.STAGE_ORDER["admission_decision"]
        return

    # the offer is dispatched by admissions after the committee decision, so the `admitted`
    # milestone is always strictly later than `admission_decision` (contract invariant F2)
    ats = dts + timedelta(hours=int(rng.integers(3, 61)))
    rec["decision_type"] = "admit"
    rec["admitted_ts"] = iso(ats)
    rec["admitted_flag"] = 1
    rec["offer_letter_issued"] = True
    offer_deadline = offer_deadline_base + timedelta(days=int(rng.integers(0, 5)))
    rec["offer_deadline"] = iso_d(offer_deadline)

    p_scholar = clip(0.14 + 0.55 * max(0.0, margin) + 0.18 * int(rec["fee_scholarship_applied"]),
                     0.0, 0.92)
    if rng.random() < p_scholar:
        rec["scholarship_offered"] = True
        rec["scholarship_amount_inr"] = int(round(
            p["annual_fee_inr"] * clip(0.10 + 0.22 * max(0.0, margin)
                                       + float(rng.normal(0, 0.05)), 0.05, 0.55) / 500) * 500)

    # ---- stage 6 -> 7 : offer acceptance ------------------------------------------------
    logit_enrol = (0.82 + 0.62 * z_intent - 0.42 * rec["_z_constraint"]
                   - 0.55 * rec["_competing"] + CHANNEL_ENROL_EFFECT[channel]
                   + 0.30 * int(rec["scholarship_offered"])
                   - 0.20 * int(rec["fee_scholarship_applied"])
                   - 0.00012 * max(0.0, (offer_deadline - ats.date()).days - 30)
                   - 0.45 * max(0.0, (p["annual_fee_inr"] - 100_000) / 100_000.0)
                   + 0.25 * (ap["region_id"] in ("REG-07", "REG-08")))
    enrolled = bool(rng.random() < sigmoid(logit_enrol))
    if enrolled:
        ets = ats + timedelta(days=float(rng.gamma(2.2, 5.5)), hours=int(rng.integers(0, 20)))
        if ets.date() > offer_deadline or ets.date() > enrol_end:
            enrolled = False
            rec["dropoff_stage"] = "admitted"
            rec["dropoff_reason"] = "offer_deadline_lapsed"
        else:
            rec["enrolled_ts"] = iso(ets)
            rec["enrolled_flag"] = 1
            rec["enrolled_given_admitted_flag"] = 1
            rec["days_decision_to_enrolled"] = (ets.date() - dts_date).days
    if not enrolled:
        rec["enrolled_given_admitted_flag"] = 0
        if rec["dropoff_stage"] is None:
            rec["dropoff_stage"] = "admitted"
            rec["dropoff_reason"] = _pick_reason(rng, "admitted")

    rec["stage_reached"] = "enrolled" if rec["enrolled_flag"] == 1 else "admitted"
    rec["stage_reached_order"] = S.STAGE_ORDER[rec["stage_reached"]]


def _realise_engagement(st: SimState, rng: np.random.Generator) -> None:
    by_app: Dict[str, List[dict]] = defaultdict(list)
    for rec in st.applications:
        window = rec["_window"]
        if not window:
            continue
        start_date, end_date = window
        n_days, total_min = rec["_eng"]
        span = (end_date - start_date).days + 1
        n_days = int(min(n_days, span))
        if n_days <= 0 or span <= 0:
            continue
        offsets = np.unique(np.clip(
            (np.sort(rng.random(n_days)) ** 0.85 * span).astype(int), 0, span - 1))
        submit_date = rec["_submit_dt"].date() if rec["_submit_dt"] else None
        first = True
        remaining = total_min
        app_rows: List[dict] = []
        for off in offsets:
            adate = start_date + timedelta(days=int(off))
            share = remaining / max(1, span - int(off))
            mins = float(np.clip(rng.gamma(2.0, max(0.6, share / 2.0)), 1.0, 240.0))
            remaining = max(0.0, remaining - mins)
            app_rows.append(dict(
                engagement_id=_next_id(st.counters, "ENG", 7),
                application_id=rec["application_id"], cycle_id=rec["cycle_id"],
                activity_date=iso_d(adate),
                days_before_submission=None if submit_date is None else (submit_date - adate).days,
                session_count=1 + int(rng.poisson(0.2 if first else 0.9)),
                total_minutes=round(mins, 1),
                pages_viewed=int(rng.poisson(2.2 + 0.9 * min(1.0, mins / 40.0))),
                docs_uploaded=int(min(4, rng.poisson(0.5 + 0.25 * min(1.0, mins / 50.0)))),
                form_fields_completed=int(min(14, rng.poisson(3.5 + 2.0 * min(1.0, mins / 45.0)))),
                device_type=S.DEVICE_TYPES[choose(rng, 3, [0.62, 0.30, 0.08] if first
                                                 else [0.52, 0.38, 0.10])],
                is_return_visit=not first,
            ))
            first = False
        st.engagement.extend(app_rows)
        by_app[rec["application_id"]] = app_rows
        if submit_date is not None:
            usable = [r for r in app_rows if date.fromisoformat(r["activity_date"]) <= submit_date]
            rec["pre_sub_session_count"] = int(sum(r["session_count"] for r in usable))
            rec["pre_sub_active_days"] = int(len(usable))
            rec["pre_sub_total_minutes"] = round(float(sum(r["total_minutes"] for r in usable)), 4)
            rec["pre_sub_doc_uploads"] = int(sum(r["docs_uploaded"] for r in usable))
            rec["pre_sub_form_fields_completed"] = int(
                sum(r["form_fields_completed"] for r in usable))
            rec["pre_sub_return_visits"] = int(sum(1 for r in usable if r["is_return_visit"]))


def _post_pass_repeat_flag(st: SimState) -> None:
    by_app: Dict[str, List[datetime]] = defaultdict(list)
    for rec in st.applications:
        if rec["_submit_dt"] is not None:
            by_app[rec["applicant_id"]].append(rec["_submit_dt"])
    for rec in st.applications:
        if rec["_submit_dt"] is None:
            continue
        ts = rec["_submit_dt"]
        rec["is_repeat_applicant_at_prediction"] = bool(
            sum(1 for t in by_app.get(rec["applicant_id"], []) if t <= ts) > 1)


def _build_events(st: SimState) -> None:
    counters = st.counters
    for rec in st.applications:
        ts_map: Dict[str, datetime] = {"prospect": rec["_inq_ts"]}
        if rec["_start_ts"] is not None:
            ts_map["application_started"] = rec["_start_ts"]
        if rec["_submit_dt"] is not None:
            ts_map["application_submitted"] = rec["_submit_dt"]
        for code, col in (("application_verified", "application_verified_ts"),
                          ("admission_decision", "admission_decision_ts"),
                          ("admitted", "admitted_ts"), ("enrolled", "enrolled_ts")):
            if rec[col]:
                ts_map[code] = parse_iso(rec[col])
        reached = rec["stage_reached"]
        prev = None
        rec["_events"] = []
        for code in S.STAGE_CODES:
            if code not in ts_map:
                break
            ts = ts_map[code]
            rec["_events"].append(dict(
                event_id=_next_id(counters, "FEV", 7),
                application_id=rec["application_id"],
                programme_id=rec["programme_id"], cycle_id=rec["cycle_id"],
                stage_code=code, stage_order=S.STAGE_ORDER[code],
                intake_round=rec["intake_round"], event_ts=iso(ts), event_date=iso_d(ts.date()),
                days_since_prev_stage=None if prev is None else (ts.date() - prev.date()).days,
                is_terminal_stage=(code == reached),
            ))
            prev = ts


# ======================================================================================
# Assembly
# ======================================================================================


def _as_bool(series: pd.Series) -> np.ndarray:
    vals = series.to_numpy(dtype=object)
    return np.array([False if v is None or v is pd.NA or (isinstance(v, float) and math.isnan(v))
                     else bool(v) for v in vals], dtype=bool)


def apply_dtypes(df: pd.DataFrame, entity: str) -> pd.DataFrame:
    ent = S.ENTITIES[entity]
    out = {}
    for c in ent.columns:
        col = df[c.name] if c.name in df.columns else pd.Series([None] * len(df))
        if c.dtype == "int64":
            out[c.name] = pd.to_numeric(col, errors="coerce").astype("Int64")
        elif c.dtype == "float64":
            out[c.name] = pd.to_numeric(col, errors="coerce").astype(float)
        elif c.dtype == "bool":
            out[c.name] = _as_bool(col)
        else:
            out[c.name] = col.astype(object).where(pd.notna(col), None)
    return pd.DataFrame(out)


def build_forecast_panel(events: List[dict], cycles_table: pd.DataFrame,
                         programs: pd.DataFrame, n_by_cell: Dict[Tuple[str, str], int],
                         min_history_weeks: int, horizons_weeks: Tuple[int, ...]) -> pd.DataFrame:
    cyc_meta = cycles_table.set_index("cycle_id")
    mondays = {cid: monday_of(date.fromisoformat(cyc_meta.loc[cid, "cycle_start_date"]))
               for cid in cycles_table["cycle_id"]}
    n_weeks = {cid: int(cyc_meta.loc[cid, "total_weeks"]) for cid in cycles_table["cycle_id"]}

    weekly = np.zeros((len(programs), len(cycles_table), max(n_weeks.values()), 7),
                      dtype=np.int64)
    pid_list = programs["programme_id"].tolist()
    cid_list = cycles_table["cycle_id"].tolist()
    pid_ix = {p: i for i, p in enumerate(pid_list)}
    cid_ix = {c: i for i, c in enumerate(cid_list)}
    stage_ix = {s: i for i, s in enumerate(S.STAGE_CODES)}

    for e in events:
        w = (date.fromisoformat(e["event_date"]) - mondays[e["cycle_id"]]).days // 7
        if 0 <= w < weekly.shape[2]:
            weekly[pid_ix[e["programme_id"]], cid_ix[e["cycle_id"]], int(w),
                   stage_ix[e["stage_code"]]] += 1
    cumulative = np.cumsum(weekly, axis=2)

    stage_col = {c: i for i, c in enumerate(S.STAGE_CODES)}
    rows = []
    for pi, pid in enumerate(pid_list):
        for ci, cid in enumerate(cid_list):
            m0 = mondays[cid]
            dec1 = date.fromisoformat(cyc_meta.loc[cid, "intake1_decision_start"])
            cend = date.fromisoformat(cyc_meta.loc[cid, "cycle_end_date"])
            sh = _split_hint(ci, len(cid_list))
            for w in range(n_weeks[cid]):
                ws = m0 + timedelta(days=7 * w)
                # An origin is eligible only if it has a full history window AND enough
                # remaining cycle weeks to observe every declared horizon H, so that
                # origin+H is always a real, non-fabricated cell of the panel.
                has_room = (w + max(horizons_weeks)) <= (n_weeks[cid] - 1)
                row = {
                    "panel_id": f"{pid}|{cid}|{iso_d(ws)}",
                    "programme_id": pid, "cycle_id": cid,
                    "week_start_date": iso_d(ws), "week_end_date": iso_d(ws + timedelta(days=6)),
                    "week_index_in_cycle": w,
                    "is_forecast_eligible": bool(w >= min_history_weeks and ws >= dec1
                                                 and ws <= cend and has_room),
                    "split_hint": sh,
                    "n_applications": int(n_by_cell.get((pid, cid), 0)),
                }
                for stage, name in (("prospect", "cum_applications_opened"),
                                    ("application_started", "cum_applications_started"),
                                    ("application_submitted", "cum_applications_submitted"),
                                    ("application_verified", "cum_applications_verified"),
                                    ("admission_decision", "cum_decisions_issued"),
                                    ("admitted", "cum_admitted"),
                                    ("enrolled", "cum_enrolled")):
                    row[name] = int(cumulative[pi, ci, w, stage_col[stage]])
                for stage, name in (("application_submitted", "wk_applications_submitted"),
                                    ("application_verified", "wk_applications_verified"),
                                    ("admission_decision", "wk_decisions_issued"),
                                    ("admitted", "wk_admitted"),
                                    ("enrolled", "wk_enrolled")):
                    row[name] = int(weekly[pi, ci, w, stage_col[stage]])
                cs = row["cum_applications_submitted"]
                ve = row["cum_applications_verified"]
                di = row["cum_decisions_issued"]
                row["cum_submit_to_verify_rate"] = round(ve / cs, 6) if cs else None
                row["cum_admit_rate"] = round(row["cum_admitted"] / di, 6) if di else None
                row["cum_enrolment_yield"] = (round(row["cum_enrolled"] / cs, 6) if cs else None)
                rows.append(row)
    return pd.DataFrame(rows)


def build_dataframes(cfg: GeneratorConfig, st: SimState, programs: pd.DataFrame,
                     regions: pd.DataFrame, cycles_table: pd.DataFrame,
                     campaigns: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    dfs: Dict[str, pd.DataFrame] = {}
    dfs["dim_funnel_stage"] = build_dim_funnel_stage()
    dfs["dim_region"] = regions
    dfs["dim_programme"] = programs
    dfs["dim_admission_cycle"] = cycles_table
    dfs["dim_campaign"] = campaigns

    apps_by_aid: Dict[str, List[dict]] = defaultdict(list)
    for rec in st.applications:
        apps_by_aid[rec["applicant_id"]].append(rec)
    ap_rows = []
    for aid, recs in sorted(apps_by_aid.items()):
        ap = st.applicants[aid]
        ap_rows.append(dict(
            applicant_id=aid, region_id=ap["region_id"], gender_band=ap["gender_band"],
            education_level=ap["education_level"],
            first_inquiry_date=iso_d(ap["first_inquiry_date"]),
            application_count=len(recs), is_repeat_applicant=bool(len(recs) > 1)))
    dfs["fact_applicant"] = pd.DataFrame(ap_rows)

    prog_order = {p: i for i, p in enumerate(programs["programme_id"])}
    cyc_order = {c: i for i, c in enumerate(cycles_table["cycle_id"])}
    prog_code = programs.set_index("programme_id")["programme_code"].to_dict()
    ordered = sorted(st.applications,
                     key=lambda r: (cyc_order[r["cycle_id"]], prog_order[r["programme_id"]],
                                    r["application_id"]))
    app_rows = []
    for rec in ordered:
        row = {k: rec.get(k) for k in APPLICANT_COLUMNS}
        row["cohort_label"] = f"{prog_code[rec['programme_id']]}-{rec['cycle_id']}"
        row["split_hint"] = _split_hint(cyc_order[rec["cycle_id"]], len(cyc_order))
        app_rows.append(row)
    dfs["fact_application"] = pd.DataFrame(app_rows)

    events: List[dict] = []
    for rec in ordered:
        events.extend(rec.get("_events", []))
    dfs["fact_funnel_event"] = pd.DataFrame(
        events if events else list(S.fact_funnel_event.column_names))
    dfs["fact_engagement"] = pd.DataFrame(
        st.engagement if st.engagement else [c.name for c in S.fact_engagement.column_names])
    dfs["fact_forecast_panel"] = build_forecast_panel(events, cycles_table, programs,
                                                      st.n_by_cell, cfg.min_history_weeks,
                                                      cfg.forecast_horizons_weeks)
    return dfs


def build_modelling_view(dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    apps = dfs["fact_application"]
    mv_apps = apps[apps["stage_reached_order"] >= 3]
    app_df = mv_apps.reset_index(drop=True)
    appl = dfs["fact_applicant"].set_index("applicant_id")
    reg = dfs["dim_region"].set_index("region_id")
    prog = dfs["dim_programme"].set_index("programme_id")
    applicant_region = app_df["applicant_id"].map(appl["region_id"])
    # the primary key of a dimension is carried on fact_application as a same-named foreign key
    fk_col = {"fact_applicant": "applicant_id", "dim_programme": "programme_id",
              "dim_admission_cycle": "cycle_id", "dim_region": "region_id",
              "fact_application": "application_id"}

    out = {}
    for m in S.MV_COLUMNS:
        if m.source_column == S.PRIMARY_KEYS.get(m.source_entity):
            out[m.name] = app_df[fk_col[m.source_entity]]
        elif m.source_entity == "fact_application":
            out[m.name] = app_df[m.source_column]
        elif m.source_entity == "fact_applicant":
            out[m.name] = app_df["applicant_id"].map(appl[m.source_column])
        elif m.source_entity == "dim_region":
            out[m.name] = applicant_region.map(reg[m.source_column])
        elif m.source_entity == "dim_programme":
            out[m.name] = app_df["programme_id"].map(prog[m.source_column])
        else:
            raise ValueError(f"unknown MV source entity {m.source_entity}")
    return pd.DataFrame(out).reset_index(drop=True)


# ======================================================================================
# IO
# ======================================================================================


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def apply_mv_dtypes(mv: pd.DataFrame) -> pd.DataFrame:
    out = {}
    for m in S.MV_COLUMNS:
        col = mv[m.name]
        src = S.ENTITIES[m.source_entity].col(m.source_column)
        if src.dtype == "int64":
            out[m.name] = pd.to_numeric(col, errors="coerce").astype("Int64")
        elif src.dtype == "float64":
            out[m.name] = pd.to_numeric(col, errors="coerce").astype(float)
        elif src.dtype == "bool":
            out[m.name] = _as_bool(col)
        else:
            out[m.name] = col.astype(object).where(pd.notna(col), None)
    return pd.DataFrame(out)


def _collect_examples(dfs: Dict[str, pd.DataFrame]) -> Dict[str, str]:
    ex: Dict[str, str] = {}
    for df in dfs.values():
        for col in df.columns:
            s = df[col].dropna()
            ex[col] = "" if len(s) == 0 else str(s.astype(str).unique()[0])
    return ex


def run(cfg: GeneratorConfig, root: Path, emit_dictionary: bool) -> Dict[str, pd.DataFrame]:
    raw_dir, proc_dir, docs_dir = root / "data" / "raw", root / "data" / "processed", \
        root / "docs"
    for d in (raw_dir, proc_dir, docs_dir):
        d.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(np.random.SeedSequence(cfg.seed).spawn(4)[3])
    regions = build_dim_region(rng)
    programs = build_dim_programme(rng)
    cycles = cycle_calendar(cfg.start_cycle_year, cfg.n_cycles)
    cycles_table = build_cycles_table(cycles, programs)
    campaigns = build_dim_campaign(rng, cycles)

    n_cells = len(programs) * cfg.n_cycles
    min_per_cell = max(10, min(cfg.min_applications_per_cell, cfg.n_applications // (n_cells * 4)))
    st = simulate(cfg, programs, regions, cycles, campaigns, min_per_cell)
    dfs = build_dataframes(cfg, st, programs, regions, cycles_table, campaigns)
    mv = build_modelling_view(dfs)

    written: Dict[str, str] = {}
    row_counts: Dict[str, int] = {}
    for name in S.ENTITIES:
        df = apply_dtypes(dfs[name], name)
        path = raw_dir / f"{name}.csv"
        df.to_csv(path, index=False, float_format=cfg.float_format, lineterminator="\n")
        written[f"data/raw/{name}.csv"] = _sha256(path)
        row_counts[name] = int(len(df))

    mv = apply_mv_dtypes(mv)
    mv_path = proc_dir / "applications_modelling_view.csv"
    mv.to_csv(mv_path, index=False, float_format=cfg.float_format, lineterminator="\n")
    written["data/processed/applications_modelling_view.csv"] = _sha256(mv_path)
    row_counts["applications_modelling_view"] = int(len(mv))

    manifest = dict(
        dataset="admitflow-synthetic-admissions", dataset_version=cfg.dataset_version,
        synthetic=True, fictuality_notice=S.FICTIONALITY_STATEMENT,
        performance_disclaimer=S.PERFORMANCE_DISCLAIMER,
        contract="docs/admitflow_data_contract.md", data_dictionary="docs/data_dictionary.md",
        generator="scripts/generate_dataset.py", schema="scripts/admitflow_schema.py",
        config=asdict(cfg), numpy_version=np.__version__, pandas_version=pd.__version__,
        row_counts=row_counts, sha256=written,
    )
    (raw_dir / "_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                            encoding="utf-8")

    if emit_dictionary:
        (docs_dir / "data_dictionary.md").write_text(
            S.render_data_dictionary(_collect_examples(dfs)), encoding="utf-8")
    return dfs


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Generate the AdmitFlow synthetic admission dataset.")
    ap.add_argument("--n-applications", type=int, default=GeneratorConfig.n_applications,
                    help="Target number of application-level records (default 28000).")
    ap.add_argument("--n-cycles", type=int, default=GeneratorConfig.n_cycles,
                    help="Number of admission cycles (default 4).")
    ap.add_argument("--start-cycle-year", type=int, default=GeneratorConfig.start_cycle_year,
                    help="Start year of the first admission cycle (default 2022).")
    ap.add_argument("--seed", type=int, default=GeneratorConfig.seed,
                    help="Master random seed (default 20240817).")
    ap.add_argument("--min-history-weeks", type=int, default=GeneratorConfig.min_history_weeks,
                    help="Minimum panel history before a week is a forecast origin (default 4).")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                    help="Project root to write into (default: parent of scripts/).")
    ap.add_argument("--emit-data-dictionary", action="store_true",
                    help="Render docs/data_dictionary.md from the schema registry.")
    args = ap.parse_args(argv)

    cfg = GeneratorConfig(n_applications=args.n_applications, n_cycles=args.n_cycles,
                          start_cycle_year=args.start_cycle_year, seed=args.seed,
                          min_history_weeks=args.min_history_weeks)
    cfg.validate()

    dfs = run(cfg, args.root, args.emit_data_dictionary)
    print("[admitflow] generated tables:")
    for name, df in dfs.items():
        print(f"  {name:24s} rows={len(df):>8d}  cols={len(df.columns):>3d}")
    fact_rows = sum(len(d) for n, d in dfs.items() if n.startswith("fact_"))
    print(f"[admitflow] fact rows total = {fact_rows}")
    print(f"[admitflow] root = {args.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
