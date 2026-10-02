# Acceptance Criteria

## Dataset and validation

- A reproducible synthetic dataset is generated from code using a fixed seed.
- Schema, validation checks, and data dictionary are documented.
- Missing values, duplicates, invalid categories, impossible dates, and numerical ranges are checked.
- A profiling report is generated and retained as evidence.

## Analytics

- Funnel stage volume, conversion, drop-offs, and comparisons are computed from the actual dataset.
- Cohort analysis supports admission cycle, programme, selectivity, and region filters.
- Programme comparison and region comparison are documented with observed results.
- Attribution reporting clearly separates descriptive observations from causal language.

## ML

- A logistic regression baseline is trained and evaluated.
- An advanced model is trained and compared against the baseline.
- Metrics such as log loss, ROC-AUC, PR-AUC, accuracy, precision, recall, F1, and confusion matrix are generated.
- Model explainability and error analysis are documented.

## Forecasting

- Forecast models are trained with leakage-safe temporal features.
- H1, H2, H4, and H6 forecasts are produced and evaluated.
- Forecast metrics are captured and governance checks are documented.

## Scenario simulation

- Scenario engine accepts meaningful funnel assumptions and returns baseline, scenario, delta, and percentage change.
- Results are deterministic and reproducible.

## Backend and security

- API endpoints provide health, analytics, forecast, scenario, and model metadata responses.
- Auth boundaries are enforced and secrets are never committed.
- Audit logging records sensitive actions without leaking tokens or passwords.

## Frontend

- Dashboard, funnel explorer, cohort explorer, programme comparison, forecasting, scenario lab, model insights, and activity sections are implemented.
- Light and dark themes work and visual quality reflects a polished SaaS-style analytics product.
- Error, loading, empty, and responsive states are present.

## Testing and evidence

- Unit, integration, failure-mode, security, and frontend tests pass.
- All outputs are backed by actual evidence stored under `evidence/`.
- Tracker entries are updated with evidence paths and status.

## Final verification

The project is considered complete only after documentation, tests, tracker status, evidence, and actual execution all agree.
