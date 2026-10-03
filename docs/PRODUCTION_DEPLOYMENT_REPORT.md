# AdmitFlow Production Deployment Report

## Deployment

- Production URL: Not publicly deployed in this workspace; the verified local runtime is `http://127.0.0.1:5173` for the frontend and `http://127.0.0.1:8000` for the API.
- Deployment platform: Not configured in the repository; no cloud deployment credentials or pipeline were provided.
- Frontend deployment: Not yet published externally.
- Backend deployment: Local FastAPI runtime verified; external hosting pending credentials.
- Database: Local SQLite for auth and local CSV-based analytical data in the current project scope.
- Deployment date: 2026-10-03 (local verification run).

## Architecture

- Frontend: Vite static build served locally; intended for static hosting.
- Backend: FastAPI + Uvicorn service running locally.
- Database: SQLite for session auth, CSV for analytics dataset.
- AI: Groq server-side integration through `GROQ_API_KEY`.
- Model: joblib artifact loaded from the repo-managed `data/models` folder.

## Environment

Required environment values for the current implementation:

- `GROQ_API_KEY` — backend only; required when the AI assistant is enabled.
- `ADMITFLOW_AI_MODEL` — optional override; defaults to `openai/gpt-oss-120b`.
- `VITE_API_BASE_URL` — frontend only; points to the backend origin.

The repository includes `.env.example` with the non-secret template. Real secrets were not committed.

## Verification

Verified behavior:

- Backend tests: 21 passed.
- Frontend tests: 4 passed.
- Production build: Vite build passed.
- Lint: passed.
- Authentication flow: login, session persistence, and invalid token cleanup succeed.
- AI assistant: provider-backed calls are gated behind `GROQ_API_KEY` and return offline mode when absent.
- Model and forecasting routes: validated through the project test suite and runtime API checks.

## Testing

- Total backend tests: 21
- Passed: 21
- Failed: 0
- Warnings: 1 FastAPI/TestClient deprecation warning
- Frontend tests: 4 passed
- Build: success
- Lint: success

## Security

- Secret file is ignored by Git.
- No hardcoded API keys or service-role credentials were found in the application source.
- API access is protected with bearer token checks for protected routes.
- Current production improvement: move from browser-stored bearer tokens to secure HttpOnly cookies if enterprise-grade security is required.

## Evidence

Evidence is stored under:

- `evidence/tests/`
- `evidence/metrics/`
- `evidence/production/`

## Known limitations

- No public cloud deployment exists because no production hosting credentials were provided.
- Local SQLite is appropriate for the current academic/demo scope but is not a high-scale production database.
- Multi-user role separation is not implemented beyond the single local admin user.
- The AI assistant requires a valid Groq key to provide live responses.
