# API Reference

Base URL for local development: `http://localhost:8000`.

## Authentication

`GET /health` and `POST /auth/login` are public. Login accepts `{"email":"admin@admitflow.local","password":"admin123"}` and returns a bearer token. The demo account and session hashes are stored in the ignored local SQLite database at `data/admitflow_auth.sqlite3`; passwords are stored as salted PBKDF2 hashes. Session tokens expire after eight hours and remain valid across backend restarts. Logout revokes the session. All `/api/*` routes require `Authorization: Bearer <token>`. Missing or invalid tokens receive HTTP 401. The credentials are local demo credentials only.

`POST /auth/logout?token=<token>` validates and revokes the session, then appends a logout event to the in-memory audit log.

## AI provider configuration

The optional AI assistant uses the Groq SDK on the backend. Configure `GROQ_API_KEY` in the backend environment or an ignored project-root `.env` file; optionally set `ADMITFLOW_AI_MODEL` (default `openai/gpt-oss-120b`). Never place provider credentials in Vite variables or frontend code. Without a key, `/api/assistant/status` reports `configured: false` and `/api/assistant` returns HTTP 503; the dashboard keeps working and the AI panel explains that the provider is offline. Assistant prompts contain aggregate analytics and, optionally, scenario assumptions whose results are recomputed server-side; applicant-level rows are not sent.

## Routes

| Method | Route | Authentication | Response |
|---|---|---|---|
| `GET` | `/health` | Public | Service health. |
| `POST` | `/auth/login` | Public | Bearer token and demo user details. |
| `POST` | `/auth/logout` | Token query parameter | Logout status. |
| `GET` | `/auth/oauth` | Public | OAuth configuration status; OAuth is not configured. |
| `GET` | `/api/dashboard` | Bearer token | Applicant, admission, enrolment, and conversion metrics. |
| `GET` | `/api/funnel` | Bearer token | Cumulative stage counts and conversion. |
| `GET` | `/api/cohorts` | Bearer token | Cycle, programme, region, and selectivity summaries. |
| `GET` | `/api/programmes` | Bearer token | Programme comparison rows. |
| `GET` | `/api/attribution` | Bearer token | Descriptive campaign-source rates. |
| `GET` | `/api/cycle` | Bearer token | Cycle-year comparison rows. |
| `GET` | `/api/forecast` | Bearer token | Holdout metrics and H1/H2/H4/H6 enrolment forecasts. |
| `GET` | `/api/scenarios` | Bearer token | Default deterministic scenario. |
| `POST` | `/api/scenarios/run` | Bearer token | Scenario from non-negative `application_volume`, optional `stage_adjustments`, and optional `campaign_shift`. Baseline stage volumes scale with application volume and are bounded to a monotonic funnel. |
| `GET` | `/api/model` | Bearer token | Trains/evaluates models and returns current metrics and feature signals. |
| `GET` | `/api/audit` | Bearer token | Most recent in-memory audit records. |
| `GET` | `/api/assistant/status` | Bearer token | Provider readiness; does not expose credentials. |
| `POST` | `/api/assistant` | Bearer token | Grounded answer from a bounded `question` and optional scenario assumptions (`application_volume`, `stage_adjustments`, `campaign_shift`); scenario outputs are recomputed on the server. Returns answer, data references, and follow-up questions. |

All campaign attribution is descriptive, not causal. Audit records are process-local and are lost when the service restarts. The `/api/model` endpoint retrains models on each request and should not be treated as a low-latency production endpoint.
