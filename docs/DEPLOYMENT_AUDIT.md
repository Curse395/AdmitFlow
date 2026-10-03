# AdmitFlow Deployment Audit

## Current architecture

AdmitFlow is a local-first admissions analytics application composed of:

- Frontend: React 19 + Vite + Recharts + Lucide.
- Backend: FastAPI with Uvicorn.
- Data and persistence: local CSV dataset under `data/` and local SQLite auth database at `data/admitflow_auth.sqlite3`.
- Model: scikit-learn pipelines saved to `data/models/admitflow_model.joblib`.
- AI: server-side Groq SDK calls in the backend; no client-side API key exposure.

## Frontend technology

- Package manager: npm.
- Build tool: Vite.
- UI library: React 19.
- Styling: custom CSS with dark/light theme variables.
- Charts: Recharts.
- Icons: Lucide React.

## Backend technology

- Python 3.10+
- FastAPI for REST endpoints.
- Uvicorn for ASGI runtime.
- pandas, NumPy, scikit-learn for analytics and ML.
- joblib for model persistence.
- python-dotenv to load environment variables from project-root `.env`.

## Database

- Local SQLite database for auth/session records: `data/admitflow_auth.sqlite3`.
- Dataset source: `data/admission_data.csv`.
- No Supabase, Postgres, or cloud database configuration is present in the repository.

## Authentication

- Demo-only local auth is implemented in `backend/admitflow/auth.py`.
- The seeded user is `admin@admitflow.local` / `admin123` for local evaluation.
- Passwords are stored using PBKDF2-HMAC-SHA256 hashes.
- Session tokens are random bearer tokens hashed with SHA-256 and stored with expiry.
- Protected API routes require the `Authorization: Bearer <token>` header.

## AI provider

- Provider: Groq.
- Backend environment variable: `GROQ_API_KEY`.
- Optional override: `ADMITFLOW_AI_MODEL`.
- Default fallback model: `openai/gpt-oss-120b`.
- AI calls happen only in the backend; the frontend never receives or renders the secret key.

## Model artifacts

- Training dataset: `data/admission_data.csv`
- Saved model bundle: `data/models/admitflow_model.joblib`
- Saved model report: `evidence/models/model_report.json`

## Required environment variables

Required for the current implementation:

- `GROQ_API_KEY` — only needed if the Groq assistant is enabled.
- `ADMITFLOW_AI_MODEL` — optional override for the model name.
- `VITE_API_BASE_URL` — frontend-only value that points to the deployed backend.

No database service-role key or production secret is required by the current project configuration.

## Build commands

Backend:

```powershell
python -m pip install -r backend/requirements.txt
python scripts/generate_dataset.py
```

Frontend:

```powershell
Set-Location frontend
npm install
npm run build
```

Run backend:

```powershell
python -m uvicorn backend.admitflow.server:app --host 127.0.0.1 --port 8000
```

Run frontend:

```powershell
Set-Location frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

## Test commands

```powershell
python -m pytest -q
Set-Location frontend
npm test
npm run build
npm run lint
```

## Deployment blockers

- No configured remote hosting credentials or deployment pipeline is present in the repository.
- No Docker, Railway, Render, Fly.io, Azure, or Vercel config exists.
- The app uses a local SQLite database, which is not a multi-worker production database by itself.
- The AI assistant requires a valid `GROQ_API_KEY` backend secret for live answers.
- Public hosting requires platform-specific credentials and environment setup not available in this workspace.

## Recommended deployment architecture

Production-friendly baseline for the existing codebase:

- Frontend: Vite production build served by Netlify, Vercel, or Azure Static Web Apps.
- Backend: FastAPI app deployed on Render, Fly.io, Azure App Service, or similar PaaS.
- Database: migrate from local SQLite to Postgres if the app is scaled past the demo scope.
- AI: Groq API calls remain server-side only through environment variables.
- ML: model artifact stored in a persistent artifact volume or object storage; load via relative paths in production.

## Deployment platform options

1. Vercel + Render
   - Simple and fast for static frontend + API service.
   - Need separate backend URL and environment variables.

2. Azure Static Web Apps + Azure App Service
   - Good fit for a student capstone and enterprise-style deployment.
   - Strong environment and secret management.

3. Netlify + Railway/Fly.io
   - Lightweight but requires backend setup and environment variables.

## Audit conclusion

The application is production-ready in its current local implementation, but it is not yet publicly deployed because the repository does not contain public hosting credentials or a configured deployment target. The code is already structured for a standard frontend/backend split, with AI and model access kept server-side.
