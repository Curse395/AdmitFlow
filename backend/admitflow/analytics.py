from __future__ import annotations

import pandas as pd

STAGE_ORDER = ["lead", "application", "submitted", "review", "admitted", "enrolled"]
STAGE_INDEX = {stage: idx for idx, stage in enumerate(STAGE_ORDER)}


def stage_summary(df: pd.DataFrame) -> pd.DataFrame:
    counts = pd.DataFrame(
        {
            "stage": STAGE_ORDER,
            "volume": [
                len(df),
                int(df["application_started"].sum()),
                int(df["submitted"].sum()),
                int(df["review"].sum()),
                int(df["admitted"].sum()),
                int(df["enrolled"].sum()),
            ],
        }
    )
    counts["conversion_rate"] = counts["volume"].div(len(df)) if len(df) else 0.0
    previous = counts["volume"].shift(1)
    following = counts["volume"].shift(-1)
    counts["from_previous_stage"] = counts["volume"].div(previous).where(previous > 0)
    counts["conversion_to_next"] = following.div(counts["volume"]).where(counts["volume"] > 0)
    for column in ("from_previous_stage", "conversion_to_next"):
        counts[column] = counts[column].astype(object).where(pd.notna(counts[column]), None)
    counts["stage_order"] = counts["stage"].map(STAGE_INDEX)
    return counts.sort_values("stage_order").reset_index(drop=True)


def funnel_overview(df: pd.DataFrame) -> dict:
    summary = stage_summary(df)
    baseline = summary[summary["stage"] == "lead"]["volume"].iloc[0] if not summary.empty else 0
    final = summary[summary["stage"] == "enrolled"]["volume"].iloc[0] if not summary.empty else 0
    return {
        "baseline_applications": int(baseline),
        "enrolled": int(final),
        "overall_conversion": round((final / baseline) * 100, 2) if baseline else 0.0,
        "stage_summary": summary.to_dict(orient="records"),
    }


def cycle_comparison(df: pd.DataFrame) -> pd.DataFrame:
    groups = df.groupby("cycle_year").agg(
        applications=("applicant_id", "count"),
        admissions=("admitted", "sum"),
        enrolments=("enrolled", "sum"),
    ).reset_index()
    groups["admission_rate"] = groups["admissions"] / groups["applications"]
    groups["enrolment_rate"] = groups["enrolments"] / groups["applications"]
    return groups.sort_values("cycle_year").reset_index(drop=True)


def programme_comparison(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("programme").agg(
        applicants=("applicant_id", "count"),
        applications=("applicant_id", "count"),
        admissions=("admitted", "sum"),
        enrolments=("enrolled", "sum"),
    ).reset_index()
    grouped["admission_rate"] = grouped["admissions"] / grouped["applications"]
    grouped["enrolment_rate"] = grouped["enrolments"] / grouped["applications"]
    return grouped.sort_values("enrolment_rate", ascending=False).reset_index(drop=True)


def region_summary(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("region").agg(
        applicants=("applicant_id", "count"),
        admissions=("admitted", "sum"),
        enrolments=("enrolled", "sum"),
    ).reset_index()
    grouped["admission_rate"] = grouped["admissions"] / grouped["applicants"]
    grouped["enrolment_rate"] = grouped["enrolments"] / grouped["applicants"]
    return grouped.sort_values("enrolment_rate", ascending=False).reset_index(drop=True)


def selectivity_summary(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("selectivity").agg(
        applicants=("applicant_id", "count"),
        admissions=("admitted", "sum"),
        enrolments=("enrolled", "sum"),
    ).reset_index()
    grouped["admission_rate"] = grouped["admissions"] / grouped["applicants"]
    grouped["enrolment_rate"] = grouped["enrolments"] / grouped["applicants"]
    return grouped.sort_values("enrolment_rate", ascending=False).reset_index(drop=True)


def cohort_summary(df: pd.DataFrame, cohort_field: str = "cycle_year") -> pd.DataFrame:
    grouped = df.groupby(cohort_field).agg(
        applicants=("applicant_id", "count"),
        admissions=("admitted", "sum"),
        enrolments=("enrolled", "sum"),
    ).reset_index()
    grouped["admission_rate"] = grouped["admissions"] / grouped["applicants"]
    grouped["enrolment_rate"] = grouped["enrolments"] / grouped["applicants"]
    grouped["sample_sufficiency"] = grouped["applicants"].apply(lambda x: "Sufficient" if x >= 80 else "Small cohort")
    return grouped.sort_values(cohort_field).reset_index(drop=True)


def attribution_summary(df: pd.DataFrame) -> pd.DataFrame:
    result = df.groupby("campaign_source").agg(
        applications=("applicant_id", "count"),
        submitted=("submitted", "sum"),
        admissions=("admitted", "sum"),
        enrolments=("enrolled", "sum"),
    ).reset_index()
    total = result["applications"].sum()
    result["share_of_applications"] = result["applications"] / total
    result["admission_conversion"] = result["admissions"] / result["applications"]
    result["enrolment_conversion"] = result["enrolments"] / result["applications"]
    result["attribution_note"] = "Descriptive attribution only; this is not proof of causal impact."
    return result.sort_values("applications", ascending=False).reset_index(drop=True)


def dashboard_metrics(df: pd.DataFrame) -> dict:
    overview = funnel_overview(df)
    return {
        "applicants": int(len(df)),
        "applications": int(len(df)),
        "admissions": int(df["admitted"].sum()),
        "enrolments": int(df["enrolled"].sum()),
        "admission_rate": round(df["admitted"].mean() * 100, 2),
        "enrolment_rate": round(df["enrolled"].mean() * 100, 2),
        "overall_conversion": overview["overall_conversion"],
    }
