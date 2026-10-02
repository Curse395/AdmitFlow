from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd

from .config import DATASET_PATH

PROGRAMMES = [
    "Data Science",
    "Computer Science",
    "Business Analytics",
    "AI Engineering",
    "Applied Mathematics",
]
SELECTIVITY = ["Broad Access", "Selective", "Highly Selective"]
REGIONS = ["North", "South", "East", "West", "Central"]
SOURCES = ["Search", "Referral", "Social", "Partner", "Event", "Direct"]
STAGE_ORDER = ["lead", "application", "submitted", "review", "admitted", "enrolled"]


def make_stage_probability(selectivity: str) -> list[float]:
    base = {
        "Broad Access": [0.32, 0.27, 0.21, 0.12, 0.06, 0.02],
        "Selective": [0.24, 0.28, 0.23, 0.15, 0.07, 0.03],
        "Highly Selective": [0.18, 0.24, 0.24, 0.18, 0.11, 0.05],
    }
    return base[selectivity]


def generate_admission_dataset(path: str | Path = DATASET_PATH, rows: int = 4200, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    records = []

    for idx in range(rows):
        cycle = int(rng.choice([2021, 2022, 2023, 2024, 2025, 2026]))
        programme = rng.choice(PROGRAMMES)
        selectivity = rng.choice(SELECTIVITY, p=[0.32, 0.48, 0.20])
        region = rng.choice(REGIONS)
        source = rng.choice(SOURCES)
        campaign = f"{source}-{rng.integers(10, 100)}"
        application_date = pd.Timestamp(f"{cycle}-01-01") + pd.Timedelta(days=int(rng.integers(0, 350)))

        academic_score = float(np.clip(rng.normal(72, 12), 40, 98))
        engagement_score = float(np.clip(rng.normal(66, 18), 20, 100))
        gpa = float(np.clip(rng.normal(3.4, 0.5), 2.1, 4.0))
        interest_score = float(np.clip(rng.normal(70, 17), 25, 98))
        outreach_count = int(rng.integers(0, 12))
        campaign_clicks = int(rng.integers(0, 25))
        distance_km = float(np.clip(rng.normal(220, 120), 10, 700))

        stage_probs = make_stage_probability(selectivity)
        stage = rng.choice(STAGE_ORDER, p=np.array(stage_probs) / np.sum(stage_probs))
        offered = 1 if stage in {"admitted", "enrolled"} else 0
        enrolled = 1 if stage == "enrolled" else 0
        submitted = 1 if stage in {"submitted", "review", "admitted", "enrolled"} else 0
        review = 1 if stage in {"review", "admitted", "enrolled"} else 0
        application_started = 1 if stage in {"application", "submitted", "review", "admitted", "enrolled"} else 0

        if programme == "Data Science":
            academic_score += 6
            interest_score += 5
        elif programme == "Computer Science":
            academic_score += 3
        elif programme == "Business Analytics":
            engagement_score += 7
        elif programme == "AI Engineering":
            academic_score += 4
            interest_score += 4

        academic_score = float(np.clip(academic_score, 0, 100))
        engagement_score = float(np.clip(engagement_score, 0, 100))
        interest_score = float(np.clip(interest_score, 0, 100))

        probability_of_enrolment = (
            0.25
            + (academic_score - 60) / 100 * 0.35
            + (engagement_score - 50) / 100 * 0.2
            + (gpa - 2.8) * 0.25
            + (interest_score - 50) / 100 * 0.2
            - (distance_km / 700) * 0.12
        )
        probability_of_enrolment = float(np.clip(probability_of_enrolment, 0.05, 0.95))

        if rng.random() < probability_of_enrolment and stage in {"review", "admitted", "enrolled"}:
            stage = "enrolled" if rng.random() < 0.55 else "admitted"
            enrolled = 1
            offered = 1
            review = 1
            submitted = 1

        if stage == "admitted":
            enrolled = 0
        if stage == "review":
            enrolled = 0
            offered = 0

        records.append(
            {
                "applicant_id": f"A{idx + 1:05d}",
                "cycle_year": cycle,
                "application_date": application_date.strftime("%Y-%m-%d"),
                "programme": programme,
                "selectivity": selectivity,
                "region": region,
                "campaign_source": source,
                "campaign_code": campaign,
                "stage": stage,
                "academic_score": round(float(academic_score), 2),
                "gpa": round(float(gpa), 2),
                "engagement_score": round(float(engagement_score), 2),
                "interest_score": round(float(interest_score), 2),
                "outreach_count": outreach_count,
                "campaign_clicks": campaign_clicks,
                "distance_km": round(float(distance_km), 2),
                "application_started": int(application_started),
                "submitted": int(submitted),
                "review": int(review),
                "admitted": int(offered),
                "enrolled": int(enrolled),
                "has_offer": int(offered),
            }
        )

    df = pd.DataFrame(records)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


def validate_dataset(df: pd.DataFrame) -> dict:
    issues = []
    stage_order = {stage: idx for idx, stage in enumerate(STAGE_ORDER)}

    if df.empty:
        issues.append("Dataset is empty.")

    missing = df.isna().sum().to_dict()
    missing_values = {k: int(v) for k, v in missing.items() if v > 0}
    if missing_values:
        issues.append(f"Missing values found: {missing_values}")

    duplicates = df.duplicated(subset=["applicant_id"]).sum()
    if duplicates:
        issues.append(f"Duplicate applicant ids: {duplicates}")

    invalid_categories = []
    if not set(df["programme"]).issubset(set(PROGRAMMES)):
        invalid_categories.append("programme")
    if not set(df["selectivity"]).issubset(set(SELECTIVITY)):
        invalid_categories.append("selectivity")
    if not set(df["region"]).issubset(set(REGIONS)):
        invalid_categories.append("region")
    if not set(df["campaign_source"]).issubset(set(SOURCES)):
        invalid_categories.append("campaign_source")
    if not set(df["stage"]).issubset(set(STAGE_ORDER)):
        invalid_categories.append("stage")
    if invalid_categories:
        issues.append(f"Invalid category values for: {invalid_categories}")

    invalid_dates = df["application_date"].apply(lambda x: pd.to_datetime(x, errors="coerce")).isna().sum()
    if invalid_dates:
        issues.append(f"Invalid application dates: {int(invalid_dates)}")

    stage_rank = df["stage"].map(stage_order)
    if ((stage_rank.rank(method="first") - stage_rank).abs() > 0).any():
        pass

    if not df["academic_score"].between(0, 100).all():
        issues.append("academic_score contains values outside 0–100.")
    if not df["gpa"].between(0, 4.5).all():
        issues.append("gpa contains values outside 0–4.5.")
    if not df["engagement_score"].between(0, 100).all():
        issues.append("engagement_score contains values outside 0–100.")
    if not df["interest_score"].between(0, 100).all():
        issues.append("interest_score contains values outside 0–100.")
    if not df["distance_km"].between(0, 2000).all():
        issues.append("distance_km contains impossible values.")

    invalid_flags = (
        (df["admitted"] == 1) & (df["has_offer"] == 0)
    ).sum()
    if invalid_flags:
        issues.append("Offer flags conflict with admitted field.")

    is_valid = len(issues) == 0
    summary = {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "missing_values": {k: int(v) for k, v in missing.items() if v > 0},
        "duplicates": int(duplicates),
        "invalid_categories": invalid_categories,
        "invalid_dates": int(invalid_dates),
        "issues": issues,
        "is_valid": is_valid,
    }
    return summary


def save_validation_report(df: pd.DataFrame, path: str | Path = "data/validation_report.json") -> dict:
    report = validate_dataset(df)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    df = generate_admission_dataset()
    print(df.head().to_string(index=False))
    print(validate_dataset(df))
