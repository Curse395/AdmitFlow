from __future__ import annotations

import pandas as pd


def baseline_snapshot(df: pd.DataFrame) -> dict:
    return {
        "applications": int(len(df)),
        "submitted": int(df["submitted"].sum()),
        "admitted": int(df["admitted"].sum()),
        "enrolled": int(df["enrolled"].sum()),
        "admission_rate": round(float(df["admitted"].mean() * 100), 2),
        "enrolment_rate": round(float(df["enrolled"].mean() * 100), 2),
    }


def scenario_engine(df: pd.DataFrame, application_volume: int = 5000, stage_adjustments: dict | None = None, campaign_shift: dict | None = None) -> dict:
    if application_volume < 0:
        raise ValueError("application_volume must be non-negative.")
    baseline = baseline_snapshot(df)
    volume_scale = application_volume / max(baseline["applications"], 1)
    stage_adjustments = stage_adjustments or {
        "submitted": 1.05,
        "admitted": 1.08,
        "enrolled": 1.04,
    }
    campaign_shift = campaign_shift or {"Search": 0.04, "Referral": 0.06, "Social": 0.02}

    scenario = {
        "applications": int(application_volume),
        "submitted": int(round(baseline["submitted"] * volume_scale * stage_adjustments.get("submitted", 1.0))),
        "admitted": int(round(baseline["admitted"] * volume_scale * stage_adjustments.get("admitted", 1.0))),
        "enrolled": int(round(baseline["enrolled"] * volume_scale * stage_adjustments.get("enrolled", 1.0))),
    }
    scenario["submitted"] = min(scenario["applications"], max(scenario["submitted"], 0))
    scenario["admitted"] = min(scenario["submitted"], max(scenario["admitted"], 0))
    scenario["enrolled"] = min(scenario["admitted"], max(scenario["enrolled"], 0))

    scenario["admission_rate"] = round(float((scenario["admitted"] / max(scenario["applications"], 1)) * 100), 2)
    scenario["enrolment_rate"] = round(float((scenario["enrolled"] / max(scenario["applications"], 1)) * 100), 2)

    difference = {
        "applications": scenario["applications"] - baseline["applications"],
        "submitted": scenario["submitted"] - baseline["submitted"],
        "admitted": scenario["admitted"] - baseline["admitted"],
        "enrolled": scenario["enrolled"] - baseline["enrolled"],
    }
    percentage_change = {
        "applications": round(float((difference["applications"] / max(baseline["applications"], 1)) * 100), 2),
        "submitted": round(float((difference["submitted"] / max(baseline["submitted"], 1)) * 100), 2),
        "admitted": round(float((difference["admitted"] / max(baseline["admitted"], 1)) * 100), 2),
        "enrolled": round(float((difference["enrolled"] / max(baseline["enrolled"], 1)) * 100), 2),
    }

    return {
        "baseline": baseline,
        "scenario": scenario,
        "difference": difference,
        "percentage_change": percentage_change,
        "campaign_shift": campaign_shift,
        "deterministic": True,
    }
