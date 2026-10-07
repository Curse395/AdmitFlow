# Testing

## Current verification commands

Run from the repository root unless noted:

```powershell
python -m pytest -q
Set-Location frontend
npm test
npm run lint
npm run build
```

Dataset, analytics, API/auth/security, assistant-provider fallback/context, scenario, and ML tests use pytest. Frontend interaction checks use Vitest, jsdom, and Testing Library. The UI tests cover auth-token propagation, theme toggle, cohort dimension selection, attribution rendering, scenario submission, AI-offline messaging, and keyboard search for live metrics.

## Evidence

- Backend test output: `evidence/tests/backend_pytest.txt`
- Frontend test output: `evidence/tests/frontend_vitest.txt`
- Frontend lint output: `evidence/tests/frontend_lint.txt`
- Production build output: `evidence/tests/frontend_build.txt`
- API status checks: `evidence/api/api_smoke.json`
- Auth boundary check: `evidence/security/auth_check.json`

Latest captured results: 20 backend tests passed, 3 frontend tests passed, frontend lint produced no diagnostics, and the production build succeeded with the documented bundle warning.

`npm run build` currently succeeds with a Vite warning that the minified JavaScript bundle exceeds 500 kB. This is a performance warning, not a build failure. See `docs/FINAL_VERIFICATION.md` for the remaining model-quality limitations.
