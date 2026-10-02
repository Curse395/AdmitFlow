from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from backend.admitflow.analytics import attribution_summary, cohort_summary, dashboard_metrics, funnel_overview, programme_comparison, region_summary, selectivity_summary
from backend.admitflow.auth import DEMO_USER_EMAIL, DEMO_USER_PASSWORD
from backend.admitflow.config import DATASET_PATH
from backend.admitflow.data_generator import validate_dataset
from backend.admitflow.forecast import forecast_horizons
from backend.admitflow.ml import save_model_report, train_model
from backend.admitflow.scenario import scenario_engine
from backend.admitflow.server import app

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    return value


def write_json(relative_path: str, payload: Any) -> None:
    path = EVIDENCE / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main() -> None:
    dataset = pd.read_csv(DATASET_PATH)
    validation = validate_dataset(dataset)
    write_json("dataset/validation_report.json", validation)

    analytics = {
        "dashboard": dashboard_metrics(dataset),
        "funnel": funnel_overview(dataset),
        "cycle_cohorts": cohort_summary(dataset, "cycle_year").to_dict(orient="records"),
        "programme_cohorts": cohort_summary(dataset, "programme").to_dict(orient="records"),
        "region_cohorts": region_summary(dataset).to_dict(orient="records"),
        "selectivity_cohorts": selectivity_summary(dataset).to_dict(orient="records"),
        "programme_comparison": programme_comparison(dataset).to_dict(orient="records"),
        "attribution": attribution_summary(dataset).to_dict(orient="records"),
    }
    write_json("metrics/analytics_report.json", analytics)
    write_json("metrics/forecast_report.json", forecast_horizons(dataset))
    write_json("metrics/scenario_report.json", scenario_engine(dataset))

    model_artifact = EVIDENCE / "models" / "admitflow_model.joblib"
    model_metrics = train_model(dataset, artifact_path=model_artifact)
    save_model_report(model_metrics, EVIDENCE / "models" / "model_report.json")

    client = TestClient(app)
    health = client.get("/health")
    unauthenticated = client.get("/api/dashboard")
    login = client.post(
        "/auth/login",
        json={"email": DEMO_USER_EMAIL, "password": DEMO_USER_PASSWORD},
    )
    token = login.json()["token"] if login.status_code == 200 else ""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    api_paths = [
        ("dashboard", "/api/dashboard"),
        ("funnel", "/api/funnel"),
        ("cohorts", "/api/cohorts"),
        ("programmes", "/api/programmes"),
        ("attribution", "/api/attribution"),
        ("forecast", "/api/forecast"),
        ("scenarios", "/api/scenarios"),
        ("model", "/api/model"),
        ("audit", "/api/audit"),
    ]
    api_results = {
        name: {"status_code": response.status_code, "ok": response.is_success}
        for name, path in api_paths
        for response in [client.get(path, headers=headers)]
    }
    scenario_response = client.post(
        "/api/scenarios/run",
        headers=headers,
        json={"application_volume": 5200, "stage_adjustments": {"submitted": 1.1, "admitted": 1.15, "enrolled": 1.08}},
    )
    api_results["scenario_run"] = {"status_code": scenario_response.status_code, "ok": scenario_response.is_success}
    write_json(
        "api/api_smoke.json",
        {
            "health_status": health.status_code,
            "login_status": login.status_code,
            "unauthenticated_dashboard_status": unauthenticated.status_code,
            "authenticated_routes": api_results,
        },
    )
    write_json(
        "security/auth_check.json",
        {
            "login_status": login.status_code,
            "unauthenticated_dashboard_status": unauthenticated.status_code,
            "authenticated_dashboard_status": api_results["dashboard"]["status_code"],
            "token_or_password_written": False,
        },
    )
    write_json(
        "reports/evidence_manifest.json",
        {
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "dataset_path": str(DATASET_PATH.relative_to(ROOT)),
            "dataset_rows": len(dataset),
            "dataset_validation_passed": validation["is_valid"],
            "model_artifact": str(model_artifact.relative_to(ROOT)),
            "generated_evidence": [
                "dataset/validation_report.json",
                "metrics/analytics_report.json",
                "metrics/forecast_report.json",
                "metrics/scenario_report.json",
                "models/model_report.json",
                "models/admitflow_model.joblib",
                "api/api_smoke.json",
                "security/auth_check.json",
                "screenshots/dashboard.png",
                "screenshots/dashboard-mobile.png",
                "screenshots/scenario.png",
            ],
        },
    )
    print(f"Dataset validation: {'PASS' if validation['is_valid'] else 'FAIL'} ({len(dataset)} rows)")
    print(f"API routes successful: {sum(result['ok'] for result in api_results.values())}/{len(api_results)}")
    print(f"Evidence written under {EVIDENCE}")


if __name__ == "__main__":
    main()
