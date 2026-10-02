# Final Verification

## Status

**Implemented and locally verified; not production-ready for admissions decisions.** Automated functionality and evidence checks pass. Predictive-model quality and the synthetic nature of the data remain material limitations.

## Verified

- Dataset generation is reproducible with seed 42; 4,200 rows and 22 columns pass validation with no missing values, duplicate IDs, invalid categories, or invalid dates.
- Funnel counts use cumulative flags, begin at all applicants, are monotonic for the generated dataset, and serialize as strict JSON.
- Cohort and programme summaries, descriptive attribution, and temporal forecast outputs are generated from the dataset. Scenario counts scale with requested application volume, remain monotonic, and reject negative volume inputs.
- All analytics routes require bearer authentication. Missing credentials return HTTP 401; local CORS allows the configured Vite origins without credential cookies.
- API smoke checks cover all ten protected route operations and pass.
- Frontend tests cover authentication headers, cohort selection, attribution, scenarios, and theme toggling.
- Backend tests pass (16), frontend tests pass (3), frontend lint is clean, and the production build succeeds; see the captured logs under `evidence/tests/`.

## Limitations

- The dataset and demo credentials are synthetic/local. The in-memory audit log is not durable.
- Classifier discrimination is weak. Holdout ROC-AUC is 0.5573 for logistic regression and 0.5195 for random forest. At threshold 0.5, the random forest predicts no positive cases. These models are not suitable for admissions decisions.
- The forecast uses only six annual observations and has a two-year holdout; its extrapolations are illustrative, not operational forecasts.
- The build succeeds but Vite warns that the minified JavaScript bundle is larger than 500 kB.
- OAuth is not configured. The local demo credential is not a production identity system.

## Evidence paths

See `docs/EVIDENCE.md` for the artifact map, `docs/MODEL_METHODOLOGY.md` for measured model results, and `docs/TESTING.md` for verification commands.
