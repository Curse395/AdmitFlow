# AdmitFlow v2

AdmitFlow is a T.Y. B.Sc. Data Science capstone project focused on admission conversion forecasting, funnel attribution, and scenario simulation.

## Project status

This repository is in the foundation phase. The project specification, architecture, plan, acceptance criteria, tracker, and evidence structure are being established before implementation begins.

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

## Verification principle

The project will only be considered complete when:

- all evidence is generated from actual execution
- every task in the tracker is linked to evidence
- all tests pass in the current environment
- documentation matches the implementation
- Git history and working tree confirm the final state

## Planned implementation flow

1. Establish project foundations and validation rules.
2. Generate and validate the synthetic dataset.
3. Build analytical pipelines for funnel, cohorts, and attribution.
4. Train and compare ML models with explainability.
5. Build forecasting and deterministic scenario simulation.
6. Implement FastAPI backend, auth, and audit logging.
7. Build the React analytics frontend.
8. Run full test suite and capture evidence.
9. Finalize documentation and project report.
