# AdmitFlow v2

AdmitFlow is a T.Y. B.Sc. Data Science capstone project focused on admission conversion forecasting, funnel attribution, and scenario simulation.

## Project status

The local analytics application, API, and dashboard are implemented. Dataset validation, analytics, model evaluation, forecasting, scenario simulation, authentication, frontend tests, and evidence capture are runnable locally. Model discrimination is weak on the synthetic data; see `docs/MODEL_METHODOLOGY.md` before interpreting its scores.

## Core objective

Build a complete, defensible analytics platform that:

- generates a realistic synthetic admission dataset
- validates the dataset and documents schema and profiling
- profiles funnel conversion, cohorts, and programme performance
- performs descriptive attribution without causal overreach
- trains and compares baseline and advanced ML models
- evaluates forecasting across multiple horizons
- provides deterministic scenario simulations
- exposes a maintainable FastAPI backend
- includes a polished React frontend with dark/light themes
- records audit activity and enforces auth boundaries
- proves all claims with actual evidence and tests

## Repository layout

- `backend/` — backend service code, APIs, model, and data processing
- `frontend/` — React application and static assets
- `data/` — generated datasets and supporting scripts
- `docs/` — project specification, architecture, plan, and acceptance criteria
- `evidence/` — screenshots, metrics, reports, and verification artifacts
- `scripts/` — operational and maintenance scripts
- `tests/` — unit, integration, API, and security tests

## Run locally

Use Python 3.10+ and Node.js 20.19+ or 22.12+. From the repository root:

```powershell
python -m pip install -r backend/requirements.txt
python scripts/generate_dataset.py
python scripts/capture_evidence.py
python -m uvicorn backend.admitflow.server:app --reload --port 8000
```

In a second terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The local demo credentials are `admin@admitflow.local` / `admin123`; they are for local evaluation only and must not be reused in a deployed system. The API creates a random JWT signing key per process unless `ADMITFLOW_JWT_SECRET` is configured with at least 32 characters. Configure a stable secret when running multiple workers or across restarts.

## Verify

```powershell
python -m pytest -q
Set-Location frontend
npm test
npm run lint
npm run build
```

Run `python scripts/capture_evidence.py` from the repository root to refresh dataset, analytics, model, forecast, scenario, API, and security evidence. Frontend test and build output is captured separately under `evidence/tests/` during final verification.

## Documentation

- `docs/DATA_DICTIONARY.md` — dataset fields, domains, and flags
- `docs/MODEL_METHODOLOGY.md` — model design, measured metrics, and limitations
- `docs/API.md` — route contracts and authentication
- `docs/TESTING.md` — commands and current test evidence
- `docs/EVIDENCE.md` — evidence map
- `docs/FINAL_VERIFICATION.md` — acceptance status and remaining risks
- `docs/FINAL_PROJECT_REPORT.md` — final project summary

## Verification principle

The project will only be considered complete when:

- all evidence is generated from actual execution
- every task in the tracker is linked to evidence
- all tests pass in the current environment
- documentation matches the implementation
- Git history and working tree confirm the final state

Current results and known limitations are recorded in `docs/FINAL_VERIFICATION.md` and `TRACKER.xlsx`.
