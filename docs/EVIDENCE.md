# Evidence Register

All machine-readable reports are generated from the current code and dataset using `python scripts/capture_evidence.py`, unless stated otherwise. The script never writes tokens or passwords. Test logs are captured by running the documented commands with output directed to the corresponding evidence file.

| Evidence | Artifact | What it verifies |
|---|---|---|
| Dataset generation and validation | `evidence/dataset/dataset_summary.json`, `evidence/dataset/validation_report.json` | Fixed-seed 4,200-row dataset; schema checks, missing values, duplicates, categories, and dates. |
| Analytics | `evidence/metrics/analytics_report.json` | Dashboard metrics, cumulative funnel, cycle/programme/region/selectivity cohorts, programme comparison, descriptive attribution. |
| Forecast | `evidence/metrics/forecast_report.json` | Temporal holdout metrics and H1/H2/H4/H6 outputs. |
| Scenario | `evidence/metrics/scenario_report.json` | Deterministic baseline, scenario, delta, and percentage change. |
| Model | `evidence/models/model_report.json`, `evidence/models/admitflow_model.joblib` | Holdout metrics, confusion matrices, feature signals, and serialized estimators. |
| API | `evidence/api/api_smoke.json` | Health, login, unauthorized rejection, protected route responses, and scenario execution. |
| Security | `evidence/security/auth_check.json` | Authentication boundary and confirmation that credentials/tokens were not written. |
| Backend tests | `evidence/tests/backend_pytest.txt` | Current pytest output. |
| Frontend tests | `evidence/tests/frontend_vitest.txt` | Current Vitest output. |
| Frontend lint/build | `evidence/tests/frontend_lint.txt`, `evidence/tests/frontend_build.txt` | Current lint and production build output. |
| UI captures | `evidence/screenshots/dashboard.png`, `evidence/screenshots/dashboard-mobile.png`, `evidence/screenshots/scenario.png` | Authenticated dashboard at desktop/mobile widths and a live doubled-volume scenario result. |
| Verification manifest | `evidence/reports/evidence_manifest.json` | Capture timestamp, dataset row count, and generated artifact list. |

Evidence describes this local synthetic-data implementation only. The model results are weak and must not be represented as validated admissions predictions.
