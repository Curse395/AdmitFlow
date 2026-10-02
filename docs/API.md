# API Reference

Base URL for local development: `http://localhost:8000`.

## Authentication

`GET /health` and `POST /auth/login` are public. Login accepts `{"email":"admin@admitflow.local","password":"admin123"}` and returns a bearer token. All `/api/*` routes require `Authorization: Bearer <token>`. Missing or invalid tokens receive HTTP 401. The credentials are local demo credentials only.

`POST /auth/logout?token=<token>` validates the token and appends a logout event to the in-memory audit log. JWT tokens expire after eight hours. The API uses an ephemeral random signing key unless `ADMITFLOW_JWT_SECRET` is provided; set a stable value of at least 32 characters for multi-worker or restart-persistent deployments.

## Routes

| Method | Route | Authentication | Response |
|---|---|---|---|
| `GET` | `/health` | Public | Service health. |
| `POST` | `/auth/login` | Public | JWT and demo user details. |
| `POST` | `/auth/logout` | Token query parameter | Logout status. |
| `GET` | `/auth/oauth` | Public | OAuth configuration status; OAuth is not configured. |
| `GET` | `/api/dashboard` | Bearer JWT | Applicant, admission, enrolment, and conversion metrics. |
| `GET` | `/api/funnel` | Bearer JWT | Cumulative stage counts and conversion. |
| `GET` | `/api/cohorts` | Bearer JWT | Cycle, programme, region, and selectivity summaries. |
| `GET` | `/api/programmes` | Bearer JWT | Programme comparison rows. |
| `GET` | `/api/attribution` | Bearer JWT | Descriptive campaign-source rates. |
| `GET` | `/api/cycle` | Bearer JWT | Cycle-year comparison rows. |
| `GET` | `/api/forecast` | Bearer JWT | Holdout metrics and H1/H2/H4/H6 enrolment forecasts. |
| `GET` | `/api/scenarios` | Bearer JWT | Default deterministic scenario. |
| `POST` | `/api/scenarios/run` | Bearer JWT | Scenario from non-negative `application_volume`, optional `stage_adjustments`, and optional `campaign_shift`. Baseline stage volumes scale with application volume and are bounded to a monotonic funnel. |
| `GET` | `/api/model` | Bearer JWT | Trains/evaluates models and returns current metrics and feature signals. |
| `GET` | `/api/audit` | Bearer JWT | Most recent in-memory audit records. |

All campaign attribution is descriptive, not causal. Audit records are process-local and are lost when the service restarts. The `/api/model` endpoint retrains models on each request and should not be treated as a low-latency production endpoint.
