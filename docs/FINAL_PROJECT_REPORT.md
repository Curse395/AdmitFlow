# AdmitFlow v2 Final Project Report

## Summary

AdmitFlow v2 is a locally runnable admission analytics capstone. It generates a deterministic synthetic applicant dataset, validates it, calculates cumulative funnel and cohort metrics, compares programmes, reports descriptive campaign attribution, trains two classifiers, evaluates annual forecasts, simulates deterministic scenarios, and exposes those outputs through an authenticated FastAPI service and React dashboard.

## Dataset and observed analytics

The fixed-seed dataset contains 4,200 synthetic applicants across six cycles (2021-2026) and five programmes. Validation found no missing values, duplicate IDs, invalid categories, or invalid dates. There are 708 admissions/offers (16.86%) and 351 enrolments (8.36%). Corrected cumulative funnel counts are 4,200 leads, 3,106 application starts, 1,983 submissions, 1,015 reviews, 708 offers, and 351 enrolments. Attribution results are descriptive associations only.

## Model and forecast findings

The baseline logistic regression has ROC-AUC 0.5573 and PR-AUC 0.0964. The random forest has ROC-AUC 0.5195 and PR-AUC 0.1037, but predicts no positive cases at the default threshold. The model workflow and feature summaries are implemented, but neither estimator demonstrates decision-quality performance.

The linear annual forecast reports MAE 14.55, RMSE 15.5726, and MAPE 0.2733 on a two-year holdout. It projects H1=74.2, H2=77.3, H4=83.5, and H6=89.7 enrolments. Six annual observations are insufficient for operational planning; values are illustrative.

## Application and verification

The FastAPI service exposes health, authentication, protected analytics, forecast, scenario, model, audit, and optional AI assistant routes. Scenario counts scale with the requested application volume, preserve monotonic stage counts, and reject negative input. The React application includes an executive dashboard, funnel, cycle/programme/region/selectivity/campaign cohorts, programme detail, descriptive attribution, forecast workspace, editable scenario lab, model intelligence, activity timeline, light/dark themes, keyboard search, and a global assistant drawer. The assistant uses the server-side Groq provider only when configured, receives aggregate data only, and returns a clear offline state without a key. The UI sends its bearer JWT with protected requests and avoids fabricated fallback metrics.

The evidence-capture script reports valid dataset checks and successful authenticated API smoke checks. Backend tests, frontend tests, lint, and build are recorded under `evidence/tests/`. Build output includes a non-blocking large-chunk warning.

## Conclusion

The project is implemented and reproducibly verified as a local synthetic-data capstone. It is not production-ready and must not be used to make real applicant decisions. The principal next steps are obtaining suitable governed real data, improving model validation and positive-class performance, expanding temporal evidence, and hardening persistent audit/identity infrastructure.
