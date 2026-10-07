# AdmitFlow Viva Preparation Manual

## How to use this manual

This manual describes the repository as inspected on 2026-10-03. The implementation is the source of truth; older planning and final-verification prose is called out where it disagrees. Paths are repository-relative. “Current run” means an actual check made while preparing this manual; captured evidence files can be older. Do not present synthetic values as observations about a real institution.

## Project summary

**Project name:** AdmitFlow (the README and specification also call the repository/project “AdmitFlow v2”).

**Official project/topic title:** **“Admission Conversion Forecasting with Funnel Attribution and Scenario Simulation”** (`docs/PROJECT_SPEC.md`).

AdmitFlow is a local admission analytics and decision-support application. Its reproducible, synthetic applicant dataset feeds descriptive funnel, cohort, programme, and campaign-source analysis; two experimental binary classifiers; a short-history linear enrolment trend forecast; and a deterministic what-if calculator. A FastAPI service exposes the computations to a React dashboard. An optional server-side Groq LLM receives selected aggregate results and answers bounded questions. The app is an academic demonstration, not an admissions management system or a validated decision tool.

### What problem it addresses

Admission teams can have applicant records but still lack a clear view of how applicant counts move across stages, how observed outcomes vary by cycle or segment, and how stated planning assumptions change arithmetic projections. Raw records alone do not make those comparisons easy to inspect. AdmitFlow aggregates the included synthetic records into a single dashboard and planning workspace.

- **Problem:** Admission data can be difficult to summarize across funnel transitions, cycles, programmes, regions, selectivity groups, and campaign sources.
- **Solution:** Generate and validate a reproducible dataset; calculate descriptive metrics; fit and report exploratory models and a linear trend forecast; calculate deterministic scenarios; expose results in an authenticated API and dashboard.
- **Expected outcome:** A student or local evaluator can inspect measured aggregates and model limitations and test explicit planning assumptions. The system does not establish causes, make applicant-level recommendations, or demonstrate real institutional impact.

**Intended users:** Local capstone evaluators and admissions/enrolment teams seeking aggregate decision support, as described by the project specification and UI. Production institutional use is not verified.

**Why the problem matters:** Understanding where volume changes can help a team decide what to investigate. A descriptive difference is a prompt for further investigation, not evidence that a programme, applicant trait, or campaign caused an outcome.

**Core objective:** Demonstrate an end-to-end, evidence-backed analytics workflow for admission conversion, forecasting, source attribution, and controlled scenario arithmetic, while communicating uncertainty and the synthetic nature of the data.

**Why it is a Data Science project:** It includes generated tabular data, validation, aggregation, cohort comparisons, supervised classification, numerical forecast evaluation, metric reporting, and interpretation limits.

**Why it is AI-powered:** An optional LLM call is integrated into the assistant. It is separate from the scikit-learn classification and forecast calculations.

**How it differs from a simple dashboard:** The UI combines descriptive aggregates with fitted model comparisons, holdout error summaries, a deterministic scenario engine, and an LLM that receives server-computed context. The additional methods do not make the results causal or decision-ready.

### Prepared project descriptions

**30 seconds**

“AdmitFlow is a local data-science capstone called ‘Admission Conversion Forecasting with Funnel Attribution and Scenario Simulation.’ It uses a reproducibly generated synthetic dataset of 4,200 applicant records to show cumulative funnel movement, compare cycles and segments, describe outcomes by campaign source, compare two exploratory enrolment classifiers, forecast annual enrolment with a linear trend, and calculate deterministic what-if scenarios. FastAPI serves the results to a React dashboard, with an optional Groq-based assistant grounded in aggregate context. The models and forecast are illustrative, and the source comparisons are not causal.”

**1 minute**

“AdmitFlow addresses the difficulty of turning applicant records into interpretable admission-flow and planning summaries. The current CSV has 4,200 synthetic records across six cycles, five programmes, five regions, three selectivity categories, and six campaign sources. A pandas backend calculates a cumulative funnel, cycle and segment summaries, programme outcomes, and descriptive campaign-source rates. Scikit-learn compares logistic regression with a random forest for the synthetic `enrolled` flag; the results show weak discrimination, so neither is suitable for decisions. A separate `LinearRegression` extrapolates annual enrolments, but there are only six annual observations and its holdout uses two of them. The Scenario Lab scales observed counts to a requested application volume and applies user-entered multipliers; it is deterministic arithmetic, not an ML forecast. FastAPI protects analytics routes with persisted SQLite-backed bearer sessions, and React visualizes the outputs. The optional Groq assistant receives aggregate server-side context, not individual applicant rows.”

**2 minutes**

“AdmitFlow is an end-to-end local analytics application for the topic ‘Admission Conversion Forecasting with Funnel Attribution and Scenario Simulation.’ The source dataset is synthetic and generated with NumPy using seed 42. It contains 4,200 rows and 22 fields, with six cycles from 2021 through 2026. Validation reports no missing values, duplicate applicant IDs, invalid categories, or invalid dates. The funnel does not count the exclusive `stage` label: it starts with all rows and sums cumulative flags such as `application_started`, `submitted`, `review`, `admitted`, and `enrolled`. The resulting counts are 4,200, 3,106, 1,983, 1,015, 708, and 351.

“Analytics group outcomes by cycle, programme, region, selectivity, and source. Attribution calculates source share and observed admission/enrolment conversion but explicitly does not estimate causal impact. The classification target is `enrolled`. Twelve selected features pass through median imputation for numerics and most-frequent imputation plus one-hot encoding for categories. A stratified random 75/25 split is used; the baseline is balanced logistic regression and the comparison model is a 200-tree random forest. The random forest reaches 91.62% accuracy by predicting no positive cases at its default threshold, so accuracy is misleading. The forecast separately aggregates enrolments by year and fits linear regression to year index. It reports H1 74.2, H2 77.3, H4 83.5, H6 89.7, but the observations are very limited.

“The scenario engine scales observed counts to a requested volume, applies stage multipliers, rounds and clamps counts to a monotonic funnel, and returns differences. The assistant is an optional Groq SDK call. The API computes aggregates and sends them with the question to the configured model; it asks for JSON and validates the response. It is not RAG and does not perform the sklearn prediction. The UI is a React/Vite single-page app with Recharts, local page state, and an optional command palette. My main conclusion is that this project demonstrates a transparent analytics workflow, but its synthetic data, weak classifiers, short forecast history, deterministic assumptions, and non-durable audit log prevent operational use.”

**5 minutes**

“Good morning. My project is AdmitFlow, and its topic is ‘Admission Conversion Forecasting with Funnel Attribution and Scenario Simulation.’ The purpose is to demonstrate how an admissions team could inspect its aggregate applicant journey and test planning assumptions in one local workspace. It is a decision-support prototype, not an application-processing platform and not a system that decides which applicants should be admitted.

“The data is generated locally by `backend/admitflow/data_generator.py`, called by `scripts/generate_dataset.py`. NumPy uses seed 42 and the generator creates 4,200 synthetic records across cycles 2021 to 2026. The saved CSV has 22 columns. Its validation report records zero missing values, zero duplicate IDs, valid categories and dates, and no issues. These are generated records, not a sample from an identified institution. Numeric and categorical values are intentionally simulated; therefore a successful model fit does not establish real-world performance.

“The backend reads the CSV with pandas. The funnel in `analytics.py` begins with every row as a lead and sums cumulative outcome flags for later stages. It reports 4,200 leads, 3,106 application starts, 1,983 submissions, 1,015 reviews, 708 admissions/offers, and 351 enrolments. The overall lead-to-enrolment rate is 8.36%. This uses the flags, not the `stage` column, which is an exclusive final-stage label. The same analytics module compares cycles and groups applicant counts and outcome rates by programme, region, selectivity, and source. The source report measures distribution and associations only. It cannot answer whether a campaign caused an admission or enrolment.

“For predictive modelling, the target is the binary `enrolled` flag. The feature list has four categorical and eight numerical features. A scikit-learn `ColumnTransformer` imputes numeric missing values with the median and categorical missing values with the most frequent category, then one-hot encodes categories. There is no scaling. A stratified 75/25 random split with random state 42 is used. Logistic regression is the baseline; the second model is a 200-tree random forest. The report contains log loss, ROC-AUC, average precision under the `pr_auc` key, accuracy, precision, recall, F1, confusion matrices, and top feature signals. The forest’s confusion matrix is 962 true negatives, zero false positives, 88 false negatives, and zero true positives. Its 91.62% accuracy therefore comes with zero recall. Neither classifier is decision-ready. The feature signals describe model associations and are not causal explanations.

“Forecasting is a separate calculation in `forecast.py`: the records are grouped by cycle year, enrolments are summed, and `LinearRegression` fits enrolments against a sequential year index. There are six observed annual rows, but the code reserves the last two as holdout and fits on the first four. It then uses that same four-cycle fit for 2027–2032 projections. The response field called `training_years` reports six, which is the total series length, not the four rows actually used for fitting. The reported holdout errors are MAE 14.55, RMSE 15.5726, and MAPE 0.2733, or 27.33%. H1, H2, H4, and H6 are 74.2, 77.3, 83.5, and 89.7. These are directional extrapolations from very little data, not guarantees.

“The Scenario Lab is deterministic, not machine learning. At the default 5,000 application volume, it scales the baseline counts from 4,200 records, applies submitted, admitted, and enrolled multipliers, rounds to integers, and clamps each stage not to exceed the preceding stage. The current expected preset produces 2,479 submissions, 910 admissions, and 435 enrolments. The output includes differences and percentage changes from baseline. A `campaign_shift` value can be returned in the output, but the current arithmetic does not apply it to counts.

“The backend is FastAPI. Public routes include health and login; analytics routes require a bearer token. Current authentication uses a local SQLite database at `data/admitflow_auth.sqlite3`, with a seeded demo user, PBKDF2 password hashes, and SHA-256 hashes of random expiring bearer tokens. There is no sign-up route, so the current UI supports only demo access. Audit events are held in a process-local list, not SQLite.

“The frontend is React 19 and Vite, with page selection held in `App.jsx`, Recharts visualizations, and a local-storage bearer token. It exposes the dashboard, funnel, cohorts, programme analysis, attribution, forecast, scenario, model comparison, audit timeline, settings, and assistant. An optional Groq assistant receives only server-computed aggregates and optional scenario results. The prompt requests evidence-bounded JSON, and Pydantic validates the shape. It is not retrieval-augmented generation: there is no vector database or document index. The API key is read only on the backend. A live assistant request succeeded in the current workspace during verification, while older saved verification prose still says no provider key was configured.

“To conclude, AdmitFlow demonstrates a traceable path from generated data through analytics and model outputs to an interactive interface. Its honest result is not that it can predict real applicants. It is that it can show the calculations and expose their limits. Future work should prioritize governed real data, temporal and subgroup validation, a refitted and uncertainty-aware forecast, account creation and identity controls, and durable audit history before any operational use.”

## Project objectives and implemented capabilities

These objectives are grounded in the project specification and source code. The objective descriptions do not imply production readiness.

| Objective | Meaning and reason | Implementation and location | Result / limitation |
|---|---|---|---|
| Reproducible dataset | Have a controlled input for the prototype and repeatable evidence. | `generate_admission_dataset()`; `scripts/generate_dataset.py`; seed 42. | 4,200 synthetic CSV rows; not institutional data. |
| Validate data | Catch selected schema/domain problems before analysis. | `validate_dataset()` in `backend/admitflow/data_generator.py`. | Reports missing values, duplicate IDs, selected categories, dates, numeric ranges, and one offer-flag conflict; does not comprehensively validate stage/flag consistency. |
| Show funnel movement | Locate volume changes between cumulative stages. | `stage_summary()`, `funnel_overview()`; Dashboard and Funnel. | Counts, rates, transition losses; descriptive only. |
| Compare groups | Find observed differences by segment and cycle. | `cohort_summary()`, `region_summary()`, `selectivity_summary()`; Cohorts. | Group counts and rates; no causal or adjusted comparison. |
| Compare programmes | Show counts/rates and per-cycle application trends. | `programme_comparison()`; `/api/programmes`; table and drawer. | Five programmes, sorted initially by enrolment rate; no explanation of causes. |
| Describe source attribution | Compare campaign-source volumes and observed outcomes. | `attribution_summary()`; `/api/attribution`; Attribution. | Share and outcome rates with explicit non-causal warning. |
| Demonstrate binary ML | Build a reproducible classifier comparison for enrolment flag. | `prepare_model_data()`, `train_model()`, `evaluate_model()` in `ml.py`. | Logistic regression and random forest metrics; weak discrimination, not usable for applicant decisions. |
| Demonstrate forecasting | Extrapolate aggregated annual enrolment and evaluate a holdout. | `evaluate_forecast()` in `forecast.py`. | Linear-regression values H1/H2/H4/H6; six annual points only, code fits forecast on first four. |
| Support what-if arithmetic | Show effects of explicit volume and stage multipliers. | `scenario_engine()` in `scenario.py`; Scenario Lab. | Deterministic output, not a causal or learned forecast. |
| Provide natural-language explanation | Let user ask about aggregates using an external LLM. | `ask_admitflow()` and `/api/assistant`; AssistantPanel. | Optional Groq-backed JSON response; can still hallucinate despite prompt constraints. |
| Protect analytics routes | Require login token for `/api/*`. | `authenticate`, `validate_token`; FastAPI dependency `get_current_user`. | Local SQLite-backed bearer sessions, 8-hour expiry and logout revocation; only a seeded demo user is provisioned. |
| Record recent activity | Inspect selected actions in the current process. | `AUDIT_LOG`, `/api/audit`, AuditPage. | In-memory list, last ten records; lost at restart. |
| Provide an interactive workspace | Make results navigable and inspectable. | React `App.jsx`, `WorkspacePages.jsx`, `Sidebar.jsx`. | Local page state, charts, tables, presets, details, settings, and responsive UI. |

### Complete implemented feature matrix

| Feature | Purpose | Frontend location | Backend/API | Data used | Algorithm/model | Output |
|---|---|---|---|---|---|---|
| Dashboard | Snapshot totals, funnel, largest observed loss, forecast preview, programme preview. | `DashboardPage` in `frontend/src/pages/WorkspacePages.jsx` | `/api/dashboard`, `/api/funnel`, `/api/cycle`, `/api/forecast`, `/api/programmes` | CSV aggregate flags and categories | Sums, ratios, annual linear trend | Metric cards, stage view, signal and charts. |
| Funnel | Inspect six stage counts and transitions. | `FunnelPage`, `StageFunnel` | `/api/funnel` | Whole CSV and cumulative flags | Sum flags; ratios and adjacent differences | Counts, lead share, previous-stage conversion, loss. |
| Cohorts | Compare cycle, programme, region, campaign source, or selectivity. | `CohortsPage` | `/api/cohorts` | CSV groups plus outcome flags | `groupby`, sums, counts, rates; sample label threshold | Bar chart, summary tiles, table. |
| Programme analysis | Compare five programmes and inspect cycle history. | `ProgrammesPage`, `ProgrammeDrawer`, `ProgrammeTable` | `/api/programmes` | Programme, cycle, outcome flags | Grouped counts and rates | Sort/filter table, volume bars, detail drawer, application trend. |
| Attribution | Compare channel application share and observed conversion. | `AttributionPage` | `/api/attribution` | `campaign_source` plus `submitted`, `admitted`, `enrolled` flags | Group counts / total; rates / source count | Source filter, share and enrolment charts, table, causal disclaimer. |
| Forecast | Show historical annual counts, projections, error metrics. | `ForecastPage` | `/api/forecast` | Cycle-year aggregate enrolments | `LinearRegression` on sequential index | Historical/projected chart, H1/H2/H4/H6, MAE/RMSE/MAPE. |
| Scenario Lab | Compare baseline to controlled volume and funnel assumptions. | `ScenarioPage` | `GET /api/scenarios`, `POST /api/scenarios/run` | Current dataset baseline plus request multipliers | Deterministic scaling, rounding, monotonic clamps | Baseline, scenario, absolute and percentage differences. |
| Model intelligence | Compare classifier metrics and inspect top transformed feature signals. | `ModelPage` | `/api/model` | 12 selected features and `enrolled` target | Logistic regression and random forest | Holdout metrics, confusion matrices (returned), top ten signals and charts. |
| Audit | Review latest process events and filter/expand them. | `AuditPage` | `/api/audit` | In-memory event records | Last-ten slice; frontend reverse/filter | Login, logout, scenario, assistant success records. |
| Authentication | Sign in, persist current bearer token in browser, sign out. | `LoginPage`, `UserPopover`, `App.jsx` | `/auth/login`, `/auth/logout` | Seeded SQLite user and session tables | PBKDF2 password verification; random token and hash | Access token and user identity; no registration interface. |
| AI assistant | Ask questions about supported aggregates. | `AssistantPanel`, `App.jsx` | `/api/assistant/status`, `POST /api/assistant` | Aggregate dashboard/funnel/programme/attribution/cohort/forecast; optional scenario | External Groq chat completion; no local ML inference | Validated JSON answer, source labels, up to three follow-ups. |
| Theme | Switch between light and dark palettes. | `App.jsx`, CSS variables in `App.css` | None | Browser localStorage | UI state | Theme persisted as `admitflow-theme`. |
| Command palette | Search pages, programme profiles, current metrics, AI action. | `CommandPalette.jsx`, `App.jsx` | None beyond already loaded data | In-memory loaded data | Case-insensitive substring filter; Ctrl/Cmd+K | Up to nine action results; no server-side search. |
| Notifications | Surface a few latest events. | `NotificationsPopover` | Existing `/api/audit` response | Audit list already in React state | Reverse and take first four | Popover; not push notifications. |
| Settings | Show account/provider status and toggle theme/sidebar. | `SettingsPage` | Assistant status already loaded | Current user and browser state | UI only | No user management or provider-key editor. |
| Mobile navigation | Collapse navigation into a mobile drawer. | `Sidebar`, `App.jsx`, CSS | None | Local React state | CSS breakpoints / state class | Responsive sidebar and scrim. |

## Architecture

```text
Person using the browser
        |
        v
React 19 + Vite SPA (App.jsx, local component state, fetch)
        |  HTTP JSON + Authorization: Bearer token
        v
FastAPI application (server.py, Pydantic request models)
        |-------------------------------|
        v                               v
pandas analytics / sklearn ML       Groq SDK (optional)
        |                               |
        v                               v
CSV dataset + model joblib          external Groq chat API
        |
        +--> SQLite is separate: local users and session-token hashes

Audit events are held in a Python in-memory list; evidence is written to JSON/joblib files.
```

This is a local layered client/server application. The CSV remains the source for analytics. SQLite is used for authentication only; it is not the analytics warehouse. There is no ORM, message broker, cloud database, upload service, or deployment manifest in the inspected repository.

### Frontend architecture

- **Entry:** `frontend/src/main.jsx` mounts `<App />` under React `StrictMode`; global base CSS is imported there.
- **Page state:** `frontend/src/App.jsx` stores a `page` string and conditionally renders page components. There is no React Router and no URL route per workspace page. Refresh returns to Dashboard after successful auth.
- **API base:** `import.meta.env.VITE_API_BASE_URL` or default `http://127.0.0.1:8000`.
- **Requests:** `fetchJson()` attaches the localStorage bearer token and JSON content type, parses JSON, and throws using `detail` or HTTP status. At login, token and user are put in localStorage. The initial authenticated load fires eleven requests concurrently through `Promise.all`; if any fails, the complete dashboard data load is treated as failed rather than rendering partial data.
- **State:** React `useState` and `useEffect`; current data is fetched into a top-level object. Scenario inputs, active page, theme, popovers, and dialogs are client-side state. Sidebar/theme/token/user preferences use localStorage selectively.
- **Components:** `Sidebar`, `CommandPalette`, `AssistantPanel`, page components and `ProgrammeDrawer` in `WorkspacePages.jsx`.
- **Charts:** Recharts `AreaChart`, `BarChart`, `ComposedChart`, `Line`, `Area`, `Bar`, axes, tooltips, and `ResponsiveContainer`. The funnel itself is custom HTML/CSS, not a Recharts funnel chart.
- **Loading/error:** Skeleton is displayed while initial requests load. A request failure makes the workspace unavailable and exposes Retry. Assistant and scenario actions have their own loading/error states. Invalid saved tokens are not automatically cleared on a 401; user sign-out clears local state.
- **Responsive/theme/motion:** CSS in `App.css` and `index.css`; breakpoints at 1180, 980, 700, and 380 px; theme colors are CSS variables on `:root[data-theme]`; prefers-reduced-motion is supported. Google Fonts are referenced in `frontend/index.html`, so font loading depends on access to Google Fonts; CSS includes fallbacks.
- **Build/test:** Vite, Vitest, jsdom, Testing Library, Oxlint. The captured build is successful with a large-chunk warning.

### Backend architecture

- **Application:** `backend/admitflow/server.py` creates a FastAPI app and CORS middleware.
- **Loading:** `load_dataset()` calls `pd.read_csv(DATASET_PATH)`; no data cache is used, so each endpoint reloads the CSV.
- **Validation:** Pydantic models constrain scenario application volume to nonnegative and assistant question length to 3–800 characters. Multipliers are generic dictionaries, not individually schema-bounded at the API layer.
- **Services:** `analytics.py`, `forecast.py`, `scenario.py`, `ml.py`, `assistant.py`, and `auth.py` hold computation/auth concerns.
- **Error handling:** Login maps failed credentials to 401. Missing/invalid bearer credentials produce 401. AI missing key/SDK gives 503; provider failure or malformed JSON gives 502. Scenario negative volume is rejected by Pydantic on API requests and by `scenario_engine()` for direct calls. Other data/model exceptions have no route-specific translation visible here and may become server errors.
- **Audit:** Appends events to `AUDIT_LOG` in memory; `/api/audit` returns only the last ten. Uvicorn may log HTTP requests, but the application audit log is not durable.

### Machine-learning architecture

`ml.py` builds one preprocessing `ColumnTransformer` and two scikit-learn `Pipeline`s. Numeric fields use `SimpleImputer(strategy="median")`; categorical fields use `SimpleImputer(strategy="most_frequent")` then `OneHotEncoder(handle_unknown="ignore")`. The estimators are logistic regression and random forest. Both are fitted on the same training split and reported against the same test set. The model endpoint retrains on request; the evidence script also writes a joblib bundle.

### AI architecture

`server.py` computes selected aggregate context for each question. `assistant.py` constructs a system instruction and sends a JSON-serialized `{question, admitflow_data}` user message to `Groq.chat.completions.create`. Default model string is `openai/gpt-oss-120b`; `ADMITFLOW_AI_MODEL` can override it. The provider is Groq; the string identifies the model requested. Response mode is JSON object; `AssistantAnswer` validates `answer`, `data_used`, and `follow_up_questions`. There is no streaming, vector search, retrieval index, tool invocation, local LLM, or ML prediction inside the assistant.

### Database and authentication architecture

Current source (`backend/admitflow/auth.py`, `config.py`) uses Python’s built-in `sqlite3` with `AUTH_DB_PATH = data/admitflow_auth.sqlite3`.

| Table | Columns | Constraints/meaning |
|---|---|---|
| `users` | `email TEXT`, `role TEXT`, `password_salt BLOB`, `password_hash BLOB`, `created_at TEXT` | `email` is the primary key. One seeded demo user is inserted if absent. |
| `sessions` | `token_hash TEXT`, `email TEXT`, `expires_at INTEGER`, `created_at TEXT` | `token_hash` primary key; `email` foreign key references `users(email)` with `ON DELETE CASCADE`; expiry is Unix seconds. |

Connections enable foreign keys and use a 10-second SQLite timeout. SQL values are bound with `?` parameters. Passwords use PBKDF2-HMAC-SHA256, 310,000 iterations, and a random 16-byte salt; unknown usernames also trigger a dummy hash calculation. A successful login creates a 32-byte random URL-safe token; only its SHA-256 hex digest is stored. Session life is eight hours. Validation looks up the digest and requires future expiry. Logout deletes that session row. `CREATE TABLE IF NOT EXISTS` is called from auth operations; no migration framework or ORM is present. The database file is ignored by `*.sqlite3` in `.gitignore`.

The only explicit indexes are the primary-key indexes on `users.email` and `sessions.token_hash`; no additional indexes are declared.

**Important:** This supports persistent demo-user/session records, not account registration. The only provisioned login is the source-defined `admin@admitflow.local` / `admin123`. There is no signup, password reset, user-management, or role-management endpoint. The browser stores the bearer token itself in localStorage; the database stores only the hash.

### Technology stack and versions

Python and frontend versions below are those reported in the configured workspace environment and lockfiles on 2026-10-03. `backend/requirements.txt` gives lower bounds, not exact pins. Exact frontend resolutions were checked in `package-lock.json` and `frontend/package-lock.json`. This table is not a claim that all versions are pinned for every install.

| Technology | Version available/resolved | Purpose | Where used |
|---|---|---|---|
| Python | 3.10.11 | Backend language/runtime | `.venv`; Python modules/scripts/tests |
| FastAPI | 0.142.2 | JSON API framework and dependency injection | `server.py` |
| Uvicorn | 0.54.0 | ASGI development server | local run command; `backend/main.py` |
| pandas | 2.3.3 | CSV loading, grouping, aggregation | analytics, forecast, ML prep |
| NumPy | 2.2.6 | Synthetic generation, numeric indexing/metrics | generator, forecast, ML |
| scikit-learn | 1.7.2 | Imputation, encoding, classifiers, regression, metrics | `ml.py`, `forecast.py` |
| joblib | 1.6.0 | Serialize model bundle | `ml.py` |
| SQLite / `sqlite3` | Python stdlib; SQLite library version not captured here | Local auth users and sessions | `auth.py` |
| PyJWT | 2.15.1 installed; **not used by current auth implementation** | Legacy dependency remains in `requirements.txt` | No current source import for auth tokens |
| python-dotenv | 1.2.4 | Load root `.env` | `config.py` |
| Groq SDK | 1.7.0 | Optional provider client | `assistant.py` |
| Pydantic | 2.13.5 | Request/response validation (FastAPI dependency) | `server.py`, `assistant.py` |
| React | 19.3.0 | UI component framework | `frontend/src` |
| React DOM | 19.3.0 | Browser mounting | `main.jsx` |
| Vite | 8.3.2 | Dev server and production build | `frontend/vite.config.js`, package scripts |
| Recharts | 3.10.1 | Data visualization | `WorkspacePages.jsx` |
| Lucide React | 1.50.0 | Interface icons | Components/pages |
| Vitest | 5.0.3 | Frontend test runner | `App.test.jsx` |
| Testing Library React | 16.3.3 | UI interaction/assertions | `App.test.jsx` |
| jsdom | 30.1.1 | Browser-like test environment | Vite test config |
| Oxlint | 1.86.0 | Frontend lint | `frontend/package.json` |
| pytest | 9.1.1 | Python tests | `tests/` |
| httpx | 0.28.1 | FastAPI TestClient transport | API tests/evidence script |
| openpyxl | 3.1.5 | Excel tracker scripts | `scripts/generate_tracker.py`, `finalize_tracker.py` |
| Node.js | v22.23.1 | Frontend tooling | npm/Vite |
| HTML/CSS/JavaScript | HTML5/CSS; JavaScript ESM (no TypeScript) | Frontend structure/styles/code | `frontend/` |

**Not in use despite architecture suggestions:** SQLAlchemy, matplotlib, seaborn, Plotly, TypeScript, Gradient Boosting, or OAuth implementation are not present in the current code paths. The root `package.json` also declares Recharts; the frontend package declares it directly.

## Data lifecycle and what happens internally

### Dataset facts

- **File:** `data/admission_data.csv`.
- **Origin:** Generated by repository code. An external source or real institution is **not verifiable from the current repository**.
- **Generation:** `generate_admission_dataset(path=DATASET_PATH, rows=4200, seed=42)` in `backend/admitflow/data_generator.py`, called by `scripts/generate_dataset.py`.
- **Shape:** 4,200 rows × 22 columns.
- **Cycles:** 2021–2026; row counts 684, 708, 708, 692, 712, 696.
- **Validation evidence:** 0 missing cells, 0 duplicate applicant IDs, no invalid listed categories, 0 invalid date strings, `is_valid: true` (`data/validation_report.json` and `evidence/dataset/validation_report.json`).
- **Target used in the classifier:** `enrolled`, with 351 ones (8.36%) and 3,849 zeros (91.64%).
- **Data nature:** Synthetic; no personally identifying real applicant data is shown in the CSV.

### Data dictionary

Loaded pandas dtypes are shown, rather than assuming semantic database types. `application_date` is an object/string after `pd.read_csv`; validation parses it temporarily but does not convert the dataset column to datetime.

| Column | Loaded dtype | Meaning/domain supported by code/docs |
|---|---|---|
| `applicant_id` | object/string | Synthetic ID `A00001` onward; uniqueness is checked. |
| `cycle_year` | int64 | Randomly selected from 2021–2026. |
| `application_date` | object/string | Generated date in the selected cycle; observed range 2021-01-01 to 2026-12-16. |
| `programme` | object/category | Data Science, Computer Science, Business Analytics, AI Engineering, Applied Mathematics. |
| `selectivity` | object/category | Broad Access, Selective, Highly Selective. |
| `region` | object/category | North, South, East, West, Central. |
| `campaign_source` | object/category | Search, Referral, Social, Partner, Event, Direct. |
| `campaign_code` | object/string | Source-prefixed synthetic code with generated numeric suffix; used in no current analysis/model feature. |
| `stage` | object/category | Exclusive final label: lead/application/submitted/review/admitted/enrolled; not used for funnel sums or classifier. |
| `academic_score` | float64 | Synthetic score; generator starts from clipped normal values and later clips to 0–100. Observed 40–100. |
| `gpa` | float64 | Synthetic GPA, clipped 2.1–4.0. |
| `engagement_score` | float64 | Synthetic 0–100 score; observed 20–100. |
| `interest_score` | float64 | Synthetic 0–100 score; observed 25–100. |
| `outreach_count` | int64 | Random integer 0–11. |
| `campaign_clicks` | int64 | Random integer 0–24. |
| `distance_km` | float64 | Synthetic distance, clipped 10–700 km. |
| `application_started` | int64 flag | Cumulative flag: started an application. |
| `submitted` | int64 flag | Cumulative flag: submitted. |
| `review` | int64 flag | Cumulative flag: reached review. |
| `admitted` | int64 flag | Offer/admission flag; 708 ones; also includes enrolled. |
| `enrolled` | int64 flag | Binary target/outcome; 351 ones. |
| `has_offer` | int64 flag | Generated equal to `admitted`; duplicated offer information. |

The `stage` frequency is lead 1,094; application 1,123; submitted 968; review 307; admitted 357; enrolled 351. These exclusive values sum to 4,200. The funnel uses cumulative flags instead: application starts 3,106; submissions 1,983; reviews 1,015; admitted 708; enrolled 351. Never substitute exclusive stage counts for cumulative funnel counts.

### Generation and validation details

The generator uses `np.random.default_rng(seed)`. It samples programme, selectivity, region, source, cycle, application date, scores, outreach, clicks, and distance. Selectivity-specific probability vectors choose an initial exclusive stage. Programme-specific score offsets are applied; scores are clipped again. A computed enrollment probability based on academic score, engagement, GPA, interest and distance is clipped to [0.05, 0.95]. For records initially in review/admitted/enrolled, a random branch may set the final stage and flags. `campaign_source` does not appear in that probability formula, so the source comparisons are not a controlled marketing experiment.

`validate_dataset()` checks empty data, null counts, duplicate `applicant_id`, membership for selected categories, parseable dates, numeric bounds, and one consistency rule: `admitted == 1` with `has_offer == 0`. It does **not** clean or mutate data. It does not comprehensively verify binary-valued flags, stage-to-flag agreement, monotonic flag consistency per applicant, date/cycle agreement, or duplicate entire rows. A stage rank calculation ends in `pass`, so the apparent stage-order section does not reject anything. State this limitation if asked about validation completeness.

### Actual preprocessing

| Step | What code does | Why/where | What it does not do |
|---|---|---|---|
| CSV parsing | `pd.read_csv(DATASET_PATH)` | Raw source for each service computation. | Does not infer/correct semantic errors or cache the frame. |
| Dataset validation | Counts/flags selected issues in `validate_dataset()`. | Generation/evidence workflow and tests. | No automated repair; does not run in every API data load. |
| Feature selection | Selects `FEATURES + ["enrolled"]`. | Prevents direct inclusion of `stage`, IDs and other labels in classifier. | No learned feature selection/search. |
| Numeric imputation | Median `SimpleImputer`. | Inside the classifier preprocessing pipeline. | Current CSV has no missing values, so it has no reported effect on this run. |
| Categorical imputation | Most-frequent `SimpleImputer`. | Inside classifier pipeline. | Current data has no missing values. |
| Encoding | `OneHotEncoder(handle_unknown="ignore")`. | Converts four categorical features for sklearn estimators; unknown inference categories do not throw encoder error. | Does not use ordinal encoding or target encoding. |
| Scaling/normalization | **None.** | Not implemented in `ml.py`. | Logistic regression sees differently scaled numeric variables. |
| Forecast feature | Builds integer `year_index` 0…5 from sorted cycle rows. | Simple ordered time surrogate in `forecast.py`. | Does not model seasonality, trend breaks, or dates within a cycle. |
| Train/test split | Stratified random 75/25, seed42, for classifiers. | Preserves target proportion in one holdout. | Not temporal, repeated, nested, or cross-validated. |
| Forecast split | First four of six annual rows fit; last two evaluated. | A chronological two-row holdout in `forecast.py`. | The same fitted four-row model is reused for future values; it is not refit using all six years. |
| Pipeline | `ColumnTransformer` inside `Pipeline` with estimator. | Keeps imputation/encoding fitted on training data for each model. | No scaling, calibration, resampling, threshold selection, or model-selection protocol. |

**Leakage nuance:** The classifier excludes direct final-stage/status fields and uses the selected input features, which reduces direct label leakage. The random split is not a temporal deployment simulation, no formal leakage audit/test exists, and dataset generation ties outcomes to synthetic processes; avoid claiming “leakage is impossible.” The project spec/acceptance docs mention leakage checks more strongly than the code implements.

## Analytics and formulas

### Dashboard metrics

`dashboard_metrics()` returns applicants and applications as `len(df)`, admissions as sum of `admitted`, enrolments as sum of `enrolled`, rates as mean flags × 100, and overall conversion from `funnel_overview()`. Thus both “applicants” and “applications” equal 4,200 in this dataset; the code does not count only `application_started` for the dashboard applications card.

### Funnel stages and observed result

Stages in order: **lead → application → submitted → review → admitted → enrolled**. Lead is every record; each later volume is the sum of the matching cumulative flag.

| Stage | Volume | Of all leads | From previous stage | Next-stage conversion |
|---|---:|---:|---:|---:|
| Lead | 4,200 | 100.00% | — | 73.95% |
| Application started | 3,106 | 73.95% | 73.95% | 63.84% |
| Submitted | 1,983 | 47.21% | 63.84% | 51.19% |
| Review | 1,015 | 24.17% | 51.19% | 69.75% |
| Admitted | 708 | 16.86% | 69.75% | 49.58% |
| Enrolled | 351 | 8.36% | 49.58% | — |

The largest absolute transition loss is application started → submitted: 3,106 − 1,983 = **1,123** records, 36.16% of the previous stage. This identifies where counts fall, not why they fall. `conversion_rate` in each stage row is a fraction of all leads; the frontend formats the fraction as percent. `overall_conversion` in the funnel response is already multiplied by 100 (8.36), so its UI formatter treats it as a percentage number.

### Cohorts

`cohort_summary(df, field)` groups by the chosen column; counts applicant IDs; sums admitted/enrolled; divides each outcome sum by applicants; and labels groups with at least 80 applicants “Sufficient,” otherwise “Small cohort.” The code does not justify 80 as a statistical power threshold. That sample label is not returned by region/selectivity helper functions, so the UI falls back to “Observed” for those dimensions. Cycle, programme, region, selectivity, and campaign source are actual options. Group ordering is by key for `cohort_summary`, while region/selectivity helpers sort by enrolment rate. The first three highlighted cards are simply the first three rows returned, not a universal ranking.

### Programme outcomes

`programme_comparison()` groups applicant rows by programme; `applicants` and `applications` both count `applicant_id`; `admissions` and `enrolments` sum flags. Rates use the programme’s row count denominator. The table defaults to descending enrolment rate in its input, but the component initially sorts by application volume descending. The detail drawer includes programme totals and cycle-wise application counts. It does not include a causal analysis or adjusted programme-effect model.

| Programme | Applicants/applications | Admissions | Enrolments | Admission rate | Enrolment rate |
|---|---:|---:|---:|---:|---:|
| Computer Science | 841 | 144 | 76 | 17.12% | 9.04% |
| AI Engineering | 864 | 147 | 78 | 17.01% | 9.03% |
| Data Science | 807 | 136 | 68 | 16.85% | 8.43% |
| Business Analytics | 850 | 144 | 67 | 16.94% | 7.88% |
| Applied Mathematics | 838 | 137 | 62 | 16.35% | 7.40% |

Computer Science has the largest observed enrolment rate by a small margin over AI Engineering; AI Engineering has the most applicant rows and enrolments. These are synthetic descriptive differences and do not show programme quality or causal effects.

### Attribution

`attribution_summary()` groups by `campaign_source` and returns applicant/application count, submitted, admissions, enrolments, share of total applications, admission conversion and enrolment conversion. It adds the literal note: “Descriptive attribution only; this is not proof of causal impact.” Frontend charts display source share and enrolment conversion; the table shows counts and both outcome rates.

| Source | Applications | Share | Admissions | Admission rate | Enrolments | Enrolment rate |
|---|---:|---:|---:|---:|---:|---:|
| Partner | 749 | 17.83% | 128 | 17.09% | 63 | 8.41% |
| Event | 718 | 17.10% | 120 | 16.71% | 56 | 7.80% |
| Direct | 716 | 17.05% | 108 | 15.08% | 48 | 6.70% |
| Referral | 678 | 16.14% | 102 | 15.04% | 58 | 8.55% |
| Social | 674 | 16.05% | 134 | 19.88% | 65 | 9.64% |
| Search | 665 | 15.83% | 116 | 17.44% | 61 | 9.17% |

Partner has the largest application count; Social has the largest observed enrolment rate. Neither statement means that a source caused those outcomes. There is no experiment, randomized assignment, counterfactual, spend/ROI field, or confounder adjustment in the code.

**Attribution vs association vs causation:** Attribution here is a reporting label for assigning observed rows to their recorded `campaign_source`. Association is a descriptive relationship between source and outcome in the grouped data. Causation would require a defensible counterfactual design and control of selection/confounding; this app does not implement one. Correct answer to “Does AdmitFlow prove a campaign caused admissions?” is **No.**

## Machine-learning implementation

### Classifiers

| Model | Type | Target/input | Main parameters | Current role |
|---|---|---|---|---|
| Logistic Regression | Supervised binary classifier | Features listed below → `enrolled` | `max_iter=2000`, `class_weight="balanced"`, `random_state=42` | Baseline; balanced class weighting attempts to give minority class more influence. |
| Random Forest Classifier | Supervised tree-ensemble binary classifier | Same split/features/target | `n_estimators=200`, `min_samples_leaf=2`, `random_state=42` | “Advanced” comparator; not automatically selected as best and not operationally suitable. |

**12 features:** categorical `programme`, `selectivity`, `region`, `campaign_source`; numeric `academic_score`, `gpa`, `engagement_score`, `interest_score`, `outreach_count`, `campaign_clicks`, `distance_km`, `cycle_year`. Target is `enrolled` converted to int.

**Excluded:** `applicant_id`, `application_date`, exclusive `stage`, `submitted`, `review`, `admitted`, `has_offer`, and campaign code are not in `FEATURES`. Excluding direct outcome/stage columns helps avoid obvious label leakage and ID noise, but is not proof of complete leakage safety.

**Training steps:** `train_test_split(test_size=0.25, random_state=42, stratify=y)`; infer categorical columns by object dtype; infer numerical as remaining columns; build imputation/encoding `ColumnTransformer`; fit both pipeline estimators; serialize `{"baseline": baseline, "advanced": advanced}` with joblib; calculate holdout metrics and feature signals. The API invokes this training function each `/api/model` call and writes a model report to `evidence/models/model_report.json`; default model bundle is under `data/models/`. The evidence-capture script saves a separate bundle under `evidence/models/`.

**Evaluation:** Holdout comprises 1,050 records, including 88 positive and 962 negative cases in the saved report. `predict()` supplies thresholded labels (default estimator behavior); `predict_proba()[:,1]` supplies positive probabilities. There is no threshold tuning, calibration, repeated split, confidence interval, cross-validation, subgroup metric report, or model selection by a defined criterion.

### Saved holdout results

| Metric | Logistic Regression | Random Forest |
|---|---:|---:|
| Log loss | 0.6611 | 0.2975 |
| ROC-AUC | 0.5573 | 0.5195 |
| PR-AUC key (scikit-learn average precision) | 0.0964 | 0.1037 |
| Accuracy | 0.6143 | 0.9162 |
| Precision | 0.1028 | 0.0000 |
| Recall | 0.4659 | 0.0000 |
| F1 | 0.1684 | 0.0000 |
| Confusion matrix `[[TN, FP], [FN, TP]]` | `[[604, 358], [47, 41]]` | `[[962, 0], [88, 0]]` |

Random Forest predicts every holdout row negative at the default threshold, yielding 91.62% accuracy because most examples are negative. It detects none of the 88 positive cases. Its ROC-AUC of 0.5195 is close to chance. The logistic model detects some positives but has 10.28% precision. Neither model demonstrates usable applicant-level discrimination.

**Feature signals:** Logistic regression reports the absolute value of the first binary-class coefficient vector; Random Forest reports impurity-based `feature_importances_`. These are not signed effects, causal estimates, or globally reliable explanations. Logistic top signal by absolute coefficient is `gpa` (0.522950); the forest’s largest importance is `academic_score` (0.119886), followed by engagement (0.115197), interest (0.112826), distance (0.112438), and GPA (0.107654). Correlated inputs can spread or distort importance.

### Relevant ML concepts in this project

| Concept | Simple explanation | Technical connection to AdmitFlow | Viva prompt and answer |
|---|---|---|---|
| Supervised learning | Learn from examples with known outcomes. | `enrolled` is supplied as a label during model fit. | “Why supervised?” Because the source rows include a target flag and the code fits classifiers against it. |
| Binary classification | Predict one of two classes. | `enrolled` is 0/1. | “Is it regression?” No, the classifier predicts a binary outcome; the forecast is the separate regression task. |
| Train/test split | Fit on one subset and evaluate on held-out records. | Random stratified 75/25 split, seed 42. | “Does this prove production accuracy?” No; one synthetic random holdout only. |
| Stratification | Keep class ratios similar between splits. | `stratify=y`. | “Why stratify?” The target is imbalanced (8.36% positive); it reduces a chance of a badly skewed split. |
| Imputation | Fill missing feature values by a rule. | Median numeric, most frequent categorical. | “Were missing values present?” Validation reports none, so the fitted imputers were part of the pipeline but did not need to replace missing cells in this dataset. |
| One-hot encoding | Represent categories as binary indicator columns. | `OneHotEncoder(handle_unknown="ignore")`. | “Why encode?” The estimators need numeric inputs; category labels have no natural numeric order. |
| Class imbalance | One label is much less frequent. | 351/4,200 are enrolled; 8.36%. | “Why can accuracy mislead?” Predict-all-negative already gets 91.62% on this holdout while recall is zero. |
| Threshold | Convert probability to a class. | `predict()` uses estimator default; no tuning implemented. | “Could threshold improve recall?” A different threshold may trade precision/recall, but this repository does not tune or validate one. |
| Generalization | Performance on future/unseen examples. | Only approximated by one random holdout on synthetic records. | “Can it generalize to an institution?” Not established; real data and temporal/external validation are absent. |
| Feature importance | Summarize which transformed inputs influenced a fitted estimator. | Absolute logistic coefficients or forest impurity importances, top ten. | “Is importance causal?” No. It is model-relative association and can be affected by correlation. |

## Metrics: formulas and project-specific interpretation

Let `TP` be true enrolled predicted enrolled; `TN` true not-enrolled predicted not-enrolled; `FP` false enrolled predictions; `FN` missed enrolled records; `N=TP+TN+FP+FN`.

| Metric | Formula/implementation | AdmitFlow result and interpretation |
|---|---|---|
| Accuracy | `(TP + TN) / N` | Share of correct thresholded classes. Forest 0.9162 looks high, but it predicts all negative and catches no enrolled case. |
| Precision | `TP / (TP + FP)`; sklearn uses `zero_division=0` | Of predicted enrolled, what fraction are enrolled. Forest 0.0; baseline 0.1028. Low baseline precision means many positive alerts are false positives. |
| Recall / sensitivity | `TP / (TP + FN)` | Of actual enrolled, fraction found. Baseline 0.4659; forest 0.0. The forest misses every positive. |
| F1 | `2 * precision * recall / (precision + recall)` | Harmonic mean of precision/recall. Baseline 0.1684; forest 0.0. It is not a measure of probability calibration. |
| ROC-AUC | Area under TPR-vs-FPR ranking curve across thresholds; TPR=`TP/(TP+FN)`, FPR=`FP/(FP+TN)` | 0.5573 baseline and 0.5195 forest are near chance ranking. It does not choose the operating threshold. |
| PR-AUC / Average Precision | `average_precision_score`; weighted sum of precision at recall increases (not trapezoid integration in this implementation). | 0.0964 baseline and 0.1037 forest. Positive-class prevalence is 8.36%; scores near this scale emphasize the weak signal. |
| Log loss | sklearn `log_loss(y, predicted_probability)`; for binary case, `-mean(y log p + (1-y) log(1-p))` with clipping safeguards | Baseline 0.6611 and forest 0.2975. Lower is better for probabilistic fit, but forest’s better log loss does not rescue its zero thresholded recall or near-chance AUC. |
| Confusion matrix | Counts actual vs predicted classes, sklearn label order 0 then 1 | Baseline `[[604,358],[47,41]]`; forest `[[962,0],[88,0]]`. Makes the imbalance failure concrete. |
| MAE | `mean(abs(actual - predicted))` | Forecast MAE 14.55 enrolments per held-out annual point, in the target’s units. |
| RMSE | `sqrt(mean((actual - predicted)^2))` | 15.5726 enrolments. Squaring makes large errors weigh more than in MAE. |
| MAPE | `mean(abs((actual - predicted)/actual))` over nonzero actuals | Report 0.2733 = 27.33%. Code skips zero actual holdout rows; if all were zero it returns 0.0. |

**Metric choice answer:** The code reports threshold-independent ranking metrics (ROC-AUC and average precision), probability loss, thresholded metrics, and confusion matrices. Under class imbalance, discuss PR-AUC, recall, precision and confusion matrix rather than claiming accuracy proves quality. No one metric is used to select a final model.

## Forecasting implementation

- **Target:** Aggregate count of `enrolled` rows per `cycle_year`; applications/admissions are also aggregated in series response but are not forecast targets.
- **Method:** `sklearn.linear_model.LinearRegression`; this is a straight-line trend, not ARIMA, Prophet, a neural model, or seasonal time series.
- **Input:** Six annual data points for 2021–2026, sorted by cycle; `year_index` is `0,1,2,3,4,5`.
- **Evaluation split:** `split = max(1, len(series)-2)`, so with six rows, training indices are 0–3 (2021–2024); holdout indices 4–5 (2025–2026). This is chronological.
- **Critical implementation nuance:** `training_years` is populated with `len(series)` (6), not the number of rows used by `model.fit` (4). The future projections reuse that same four-row fitted model and are not refit on all six observations. The “six annual observations” displayed correctly describes available history but not fit size.
- **Future years:** 2027–2032. Future indices are 6–11; H1=2027, H2=2028, H4=2030, H6=2032.
- **Observed annual enrolments:** 2021 60; 2022 54; 2023 58; 2024 69; 2025 59; 2026 51.
- **Forecast output:** H1 74.2; H2 77.3; H4 83.5; H6 89.7. They are rounded to two decimals and not clamped to nonnegative integers.
- **Metrics:** Holdout MAE 14.55, RMSE 15.5726, MAPE 0.2733 (27.33%). There are only two test points. MAPE calculation ignores zero-valued actuals.
- **Frontend flow:** on initial workspace load `App.jsx` requests `/api/forecast`; result is saved in React state as `data.forecast`. Dashboard previews H1; Forecast displays line chart, horizons, and errors. No separate forecast button/training job is required.

**What is forecasting?** Estimating future values from time-ordered observations. Here it means extrapolating an annual linear trend in synthetic enrolment totals.

**Why forecast?** The stated project objective is to give a directional planning outlook beyond descriptive historical metrics.

**Why this method?** The source uses a simple, transparent scikit-learn linear regression on a numeric year index. Do not claim the repository tested alternatives and selected it as best; it does not.

**Limitations:** Six annual points, four used for actual fit, two for evaluation; short holdout, no uncertainty interval, no seasonality/covariates, synthetic counts, and no full-history refit for future values. Treat as illustrative.

**Defensible improvement:** Fit a final model on all historical data after evaluation, correct the reported fit-count field, compare against naïve baselines, collect more cycles, use rolling-origin evaluation and prediction intervals, and assess stability. These are future scope, not current code.

## Scenario Lab

### Inputs and defaults

- `application_volume`: nonnegative integer, API default 5,000. UI slider 0–10,000, 100 step; exact-number input has step 1.
- Multipliers: `submitted`, `admitted`, `enrolled`. UI sliders 0.50×–1.50× in 0.01 steps.
- UI presets: Conservative = 4,200 and all three multipliers 0.98; Expected = 5,000 with 1.05/1.08/1.04; Growth = 6,000 with 1.08/1.10/1.12.
- Backend default campaign-shift metadata: Search 0.04, Referral 0.06, Social 0.02. UI does not expose a campaign-shift control and the calculation never applies this object to counts; it is returned as metadata only.

### Exact calculation

Let baseline counts be `B_apps`, `B_sub`, `B_adm`, `B_enr`; requested applications `A`; scale factor `s = A / max(B_apps, 1)`; submitted/admitted/enrolled multipliers `m_sub`, `m_adm`, `m_enr`.

```text
S_apps = A
S_sub  = round(B_sub * s * m_sub)
S_adm  = round(B_adm * s * m_adm)
S_enr  = round(B_enr * s * m_enr)
S_sub  = clamp(S_sub, 0, S_apps)
S_adm  = clamp(S_adm, 0, S_sub)
S_enr  = clamp(S_enr, 0, S_adm)
```

Rates are `S_adm / max(S_apps,1) * 100` and `S_enr / max(S_apps,1) * 100`. For each stage, `difference = scenario - baseline`; `percentage_change = difference / max(baseline,1) * 100`. Python `round()` is used; the app does not model stochastic variation.

### Worked current example

Baseline is 4,200 applications, 1,983 submitted, 708 admitted, 351 enrolled. Expected preset requests 5,000 applications, so `s=5000/4200=1.190476…`.

- Submitted: `round(1983 × 1.190476… × 1.05) = round(2478.75) = 2479`.
- Admitted: `round(708 × 1.190476… × 1.08) = round(910.29) = 910`.
- Enrolled: `round(351 × 1.190476… × 1.04) = round(434.67) = 435`.
- Clamp order remains 5,000 ≥ 2,479 ≥ 910 ≥ 435.
- Enrolment rate: `435 / 5000 × 100 = 8.70%`.
- Enrolment difference: `435 − 351 = +84`, or `84/351 × 100 = 23.93%` (rounded).

Saved `evidence/metrics/scenario_report.json` records the Expected default. It is a deterministic scenario calculation, not ML prediction, statistical simulation, causal forecast, or proof an intervention will create those outcomes. The campaign shift does not affect this example’s counts.

## AI implementation and viva answers

### Request path

```text
AssistantPanel question
  -> App.askAssistant() checks status/configuration
  -> fetch POST /api/assistant with question and optional scenario
  -> FastAPI validates AssistantRequest
  -> server loads CSV and computes dashboard/funnel/programme/attribution/cohort/forecast aggregates
  -> optional scenario is recomputed server-side
  -> assistant.py serializes question + aggregates into Groq messages
  -> Groq model returns JSON object
  -> Pydantic validates AssistantAnswer
  -> API responds; React displays answer, source labels, and follow-ups
```

- **Provider/model:** Groq SDK; default model string `openai/gpt-oss-120b`, override `ADMITFLOW_AI_MODEL`.
- **Key:** `GROQ_API_KEY`, loaded from process environment or root `.env` by `config.py`. It is read in backend Python, not Vite/frontend source. Never place the key in a viva slide, source, screenshot, or shared document.
- **Status semantics:** `/api/assistant/status` only checks whether the environment variable is truthy. It does not validate the key or call the provider.
- **Prompt:** The system message instructs concise answers grounded only in aggregate context; forbids invented metrics/causes; asks to distinguish association from causation; says not to reveal hidden reasoning; requests JSON with `answer`, `data_used`, `follow_up_questions`.
- **Data passed:** dashboard totals; funnel counts/rates; programme comparison; source attribution; cohort aggregates for cycle, programme, region, selectivity, campaign source; forecast; and optional server-recomputed scenario. Applicant-level rows are not serialized to the LLM.
- **Response:** `response_format={"type":"json_object"}`, temperature 0.2. `AssistantAnswer` requires a non-empty answer, `data_used` list, and up to three follow-up questions. No streaming.
- **Failures:** No key → HTTP 503. Missing Groq SDK → 503. Invalid provider JSON/shape or provider exception → 502. The frontend shows an error; without configured status, it disables suggestions/composer and says no question is sent. Analytics remain usable.
- **Audit:** Only a successfully returned assistant answer appends `assistant_question`; failed attempts are not appended in this route.
- **Verification:** A real authenticated request returned 200 during current workspace work on 2026-10-03. The saved old `docs/FINAL_VERIFICATION.md` says no key/live response, so it is stale for that point in time; current provider availability can later change.

### Common AI answers

- **“How does the AI know the admission data?”** It does not independently connect to the CSV. The API loads the CSV, calculates named aggregates, and includes those values in the prompt for each request.
- **“Is this RAG?”** No. There is no embedding model, vector store, document retrieval, or indexed corpus. It is prompt-time context injection of structured aggregate calculations.
- **“How do you prevent hallucinations?”** The prompt says use only supplied aggregates, do not invent metrics or causes, and cite source labels; JSON shape is validated. These are guardrails, not a guarantee. Provider outputs can still be wrong.
- **“How are sensitive records handled?”** The route passes aggregate metrics rather than individual CSV rows. The dataset is synthetic. The provider call is external; an institution would need privacy, contractual, and data-governance review before sending real aggregates or using this integration.
- **“Does the AI perform the ML prediction?”** No. sklearn computes classifier metrics and forecast values; the LLM explains supplied aggregates and scenario results in natural language.
- **“Why need an LLM?”** It offers a question-and-answer interface over already calculated data. It is supplementary and can be unavailable without removing core analytics.
- **“What happens if Groq fails?”** The assistant route returns 502, the UI displays an error. Missing configuration is 503/offline. The app has no local LLM fallback.

## Backend endpoints

All current route declarations are in `backend/admitflow/server.py`. FastAPI also exposes its standard OpenAPI docs unless disabled; no custom API version prefix is used. `/api/*` endpoints use `Depends(get_current_user)`.

| Method/path | Purpose/input | Auth | Processing / output / failure behavior |
|---|---|---|---|
| `GET /health` | Liveness | Public | Returns `{status:"ok", service:"AdmitFlow API"}`. |
| `POST /auth/login` | JSON `{email,password}` | Public | SQLite-backed authentication; returns bearer token and `{email,role}`; invalid credentials 401. |
| `POST /auth/logout?token=…` | Session token in query string | Public route, validates token | Deletes session, returns logged_out; invalid/expired token 401. Query-string token placement is a logging/security weakness. |
| `GET /auth/oauth` | OAuth status | Public | Always reports not configured; no OAuth provider integration. |
| `GET /api/dashboard` | None | Bearer | CSV totals and rates. |
| `GET /api/funnel` | None | Bearer | Stage counts, rates and overall conversion. |
| `GET /api/cohorts` | None | Bearer | Cycle/programme/campaign-source cohort summaries plus region/selectivity summaries. |
| `GET /api/programmes` | None | Bearer | Programme totals and per-cycle applications/enrolment trend rows. |
| `GET /api/forecast` | None | Bearer | Linear forecast series, H1/H2/H4/H6, holdout errors. |
| `GET /api/scenarios` | None | Bearer | Backend-default scenario with default assumptions. |
| `POST /api/scenarios/run` | `application_volume`, optional dicts `stage_adjustments`, `campaign_shift` | Bearer | Validates nonnegative volume, calls deterministic engine, appends scenario event, returns baseline/scenario/differences. |
| `GET /api/assistant/status` | None | Bearer | Returns configured boolean and provider name or null; does not verify credential validity. |
| `POST /api/assistant` | `question` (3–800 chars), optional scenario object | Bearer | Computes aggregates, makes Groq request; returns validated answer; 503/502 as above. |
| `GET /api/model` | None | Bearer | Retrains models on current CSV, saves default joblib bundle and evidence model report, returns metrics. Potentially slow. |
| `GET /api/audit` | None | Bearer | Returns last ten in-memory events. |
| `GET /api/attribution` | None | Bearer | Source grouped outcomes and descriptive rates. |
| `GET /api/cycle` | None | Bearer | Cycle totals and rates. |

### Request and response details to remember

- `ScenarioRequest.application_volume`: integer ≥0, default 5,000; multipliers/shift use untyped `dict | None` fields.
- `AssistantRequest.question`: string length 3–800; `scenario` optional `ScenarioRequest`.
- `AssistantAnswer.answer`: min length 1; `data_used` list required; follow-up list defaults empty, maximum length 3.
- Missing/invalid bearer credentials produce 401. `get_current_user` catches any token-validation exception and returns “Invalid token.” Role is in the token/session result but no role-specific authorization check exists.
- CORS allows only `http://localhost:5173` and `http://127.0.0.1:5173`, all methods/headers, and `allow_credentials=False`.

## Formula sheet

The following formulas correspond to calculations in this repository; terms such as conversion are descriptive ratios over these synthetic rows.

| Formula | Variables / use | Worked project example | Viva question |
|---|---|---|---|
| `N = len(df)` | Dataset/applicant base. | `N=4,200`. | “What is the funnel denominator?” All rows, used as lead base. |
| `V_application = Σ application_started` | Application-start volume. | 3,106. | “Do you use `stage`?” No, this sum uses cumulative flags. |
| `V_stage = Σ flag_stage` | Submitted/review/admitted/enrolled count. | Submitted 1,983; enrolled 351. | “Why sum flags?” They encode cumulative milestone reach. |
| `stage_share = V_stage / N` | Rate relative to all rows; response fraction. | `351/4200=0.08357`, UI displays 8.36%. | “What is overall conversion?” Final enrolled / lead base. |
| `transition_rate_i = V_i / V_(i-1)` | Conversion from previous stage. | `1983/3106=63.84%` app-start to submitted. | “How do you find bottleneck?” Compare volume losses/transition rates, without causal explanation. |
| `loss_i = V_(i-1)-V_i` | Adjacent volume loss. | `3106−1983=1123`. | “What is largest current loss?” Application-start to submitted. |
| `dashboard_rate = mean(binary_flag) × 100` | Admissions/enrolment percentage over all rows. | `mean(enrolled)×100=8.36%`. | “Why is rate 8.36?” 351 positive flags over 4,200 rows. |
| `group_rate = group_sum(outcome)/group_count(applicant_id)` | Cohort/programme/region/selectivity/source outcome rate. | Social enrolment `65/674=9.64%`. | “Adjusted rate?” No, simple group denominator. |
| `source_share = source_applications / total_applications` | Share of total source-associated rows. | Partner `749/4200=17.83%`. | “Does share measure ROI?” No spend or causal return is modeled. |
| `p_enrol = clip(0.25 + (academic−60)/100×0.35 + (engagement−50)/100×0.2 + (gpa−2.8)×0.25 + (interest−50)/100×0.2 − (distance/700)×0.12, 0.05, 0.95)` | Synthetic generator probability used in a branch for certain intermediate/final initial stages. | Each row value depends on generated scores and distance; no real institution probability. | “Is this the ML prediction?” No; it is part of synthetic data generation. |
| `sigmoid(z)=1/(1+e^(−z))` | Logistic-regression probability model concept used inside sklearn. `z=β0+Σβjxj`. | The code fits sklearn `LogisticRegression`; it does not manually calculate coefficients. | “What does logistic regression output?” Probability-like binary class score then a thresholded class. |
| `forest_probability ≈ mean(tree_probability)` | Conceptual probability aggregation for forest; sklearn implementation controls details. | 200 trees, default classifier configuration except listed params. | “Is this hand-coded?” No, sklearn `RandomForestClassifier`. |
| `scale = A / max(B_apps,1)` | Scenario scale factor. | `5000/4200=1.190476…`. | “Why scale?” To carry baseline rates/count relationship to requested volume. |
| `S_sub=round(B_sub×scale×m_sub)` (same pattern admitted/enrolled) | Scenario stage projection before clamp. | `round(1983×1.190476×1.05)=2479`. | “Is it forecast ML?” No, deterministic arithmetic. |
| `clamp(x,0,upper)` | Enforce nonnegative monotonic funnel. | `S_adm ≤ S_sub`; `S_enr ≤ S_adm`. | “What if multipliers violate funnel?” Later stage is capped at prior stage. |
| `delta = scenario − baseline` | Scenario absolute difference. | Enrolments `435−351=+84`. | “What is the meaning?” Difference under assumptions only. |
| `delta_pct = delta / max(baseline,1) × 100` | Scenario percentage change. | `84/351×100=23.93%`. | “Why max?” Avoid zero denominator for zero baseline. |
| `y = β0 + β1 × year_index` | LinearRegression trend in forecast. | Indices 0–5 map sorted cycles 2021–2026; future indices 6–11. | “Which features forecast?” Only year index in the model. |
| `MAE=Σ|y−ŷ|/n` | Forecast error in enrolment units. | 14.55 for two holdout cycles. | “How interpret?” Average absolute miss about 14.55 enrolments across just two points. |
| `RMSE=sqrt(Σ(y−ŷ)^2/n)` | Forecast error, penalizes larger residuals. | 15.5726. | “Why larger than MAE?” Squaring weights large errors more. |
| `MAPE=mean(|(y−ŷ)/y|)` for `y≠0` | Relative forecast error. | 0.2733, displayed as 27.33%. | “What about zero?” Code excludes zero actuals; if all zero, returns 0.0. |
| `accuracy=(TP+TN)/N` | Class-label correctness. | Forest `(962+0)/1050=91.62%`. | “Is it good?” Not by itself under severe imbalance. |
| `precision=TP/(TP+FP)` | Reliability of positive predictions; sklearn zero-div handling. | Forest 0 because it predicts no positives. | “What does low precision mean?” Many predicted positives are false, baseline here. |
| `recall=TP/(TP+FN)` | Positive-case detection. | Forest `0/(0+88)=0`. | “Why critical?” Every enrolled holdout record is missed by forest. |
| `F1=2PR/(P+R)` | Precision/recall harmonic mean. | Both terms zero for forest → implementation reports 0. | “What does it omit?” Calibration and costs of errors. |
| `logloss=−mean[y ln(p)+(1−y)ln(1−p)]` | Probability quality (binary; sklearn includes safeguards). | Logistic 0.6611, RF 0.2975. | “Does lower settle model choice?” No; forest still zero recall and near-chance ROC-AUC. |

## Security, persistence, audit and failure modes

### Actual security mechanisms

- Local demo login is the only account creation path; credentials are source constants and documented in README. Never use them in deployment.
- PBKDF2-HMAC-SHA256, 310,000 iterations and 16-byte random salt protect the stored password hash. Password itself is not stored in SQLite.
- Authentication returns a random bearer token; only SHA-256 token digest is stored in SQLite. Eight-hour expiry and explicit logout deletion are implemented.
- All `/api/*` routes use bearer authentication. There is no role-based authorization policy beyond requiring a valid session; role `admin` is returned.
- Parameterized SQLite statements are used for user/session values; foreign keys are enabled.
- Groq key is backend environment-only, not sent in frontend bundle; errors do not intentionally include key.
- CORS is limited to two local frontend origins and cookies are not enabled.
- Request models constrain assistant question length and nonnegative scenario application volume.

### Not implemented / risks to acknowledge

- No registration, verification, password reset, account lockout, rate limiting, MFA, role management, user deletion, or external OAuth; `/auth/oauth` returns false.
- Demo credential is fixed in source; this is local-evaluation only.
- Bearer token is held in browser localStorage, not an HTTP-only secure cookie. A successful script injection could read it; no explicit CSP is configured in the inspected source. React escaping helps ordinary text rendering but is not a complete security program.
- Logout passes token as a query parameter. Query strings may be recorded in access logs or intermediaries; a POST body/header design would be safer.
- No TLS/production deployment configuration is present. `backend/main.py` runs host `0.0.0.0` if executed directly; the README’s dev command uses Uvicorn local defaults.
- No CSRF cookie mechanism is implemented; bearer header is used instead. No API rate limiting or request audit persistence.
- SQLite auth DB is local, one-file persistence; no migration tool, backup/restore or multi-host database configuration.
- `AUDIT_LOG` is process memory and loses all events on restart. Only successful login/logout/scenario/assistant events are appended; failed authentication/AI attempts are not consistently audited.
- Data checks are not run automatically before every analysis request.

### Error/failure behavior

| Failure | Observed handling |
|---|---|
| Wrong login | `authenticate()` raises ValueError; route returns 401. |
| Missing/invalid/expired token | `get_current_user()` returns 401. |
| Stale browser token | Frontend requests fail; loadData shows Workspace unavailable. Token/user remain stored until logout clears them. |
| Missing `GROQ_API_KEY` | Assistant API returns 503; status reports unconfigured; UI disables prompt actions and explains offline state. |
| Missing Groq SDK | 503 with SDK-not-installed detail. |
| Groq/network/other provider exception | 502 generic provider error; no local LLM fallback. |
| Invalid model JSON/schema | 502 invalid response. |
| Negative scenario volume | Pydantic rejects API payload; direct scenario call raises ValueError. |
| Missing CSV/malformed columns/model error | No dedicated route fallback is implemented; requests can fail with server errors. |
| Empty search matches | Command palette shows “No matching pages or programmes.” |
| Empty chart/table data | Several components show explicit empty messages; main initial `Promise.all` failure is not partial. |

## Audit page

`server.py` appends dictionaries to `AUDIT_LOG`: successful `login` (includes email), `logout`, `scenario_execution` (volume), and `assistant_question` on success. `GET /api/audit` returns `AUDIT_LOG[-10:]`. `AuditPage` reverses the records, filters by action, formats timestamps in browser locale, and expands event fields. Notifications take the most recent four from loaded audit data. This supports an in-process activity view, not durable compliance auditability; events disappear on restart and there is no append-only or tamper-resistant storage.

## Tests and evidence

### Test inventory

| File | What it checks |
|---|---|
| `tests/test_analytics.py` | Funnel stage order/shape, monotonic volumes, JSON-safe nulls, cycle comparison. |
| `tests/test_api.py` | Health, bearer protection, local CORS, assistant offline/mocked scenario context, login/dashboard/funnel/forecast/cohorts/programmes/attribution/scenario/audit/logout, invalid login. |
| `tests/test_assistant.py` | Missing-key 503 and mocked Groq call/validated response. |
| `tests/test_auth.py` | Valid/invalid login; salted password/session hash storage, DB reinitialization persistence and token revocation (new current auth coverage). |
| `tests/test_data_validation.py` | Real CSV validation success, no duplicate ID and no invalid dates. |
| `tests/test_ml.py` | Trains both models to temp joblib path and checks metrics/top ten features. |
| `tests/test_scenario.py` | Scenario output keys, deterministic proportional scaling, monotonic counts and negative-input rejection. |
| `tests/test_security.py` | Token round trip and bad password rejection. |
| `frontend/src/App.test.jsx` | Login card/theme, mock fetch bearer propagation, cohort selection, attribution, scenario request, assistant-offline UI, command palette interaction. |

**Evidence vs current run:** Saved `evidence/tests/backend_pytest.txt` records 20 passed; `docs/TESTING.md` and `docs/FINAL_VERIFICATION.md` also say 20. After the SQLite auth tests were present, a fresh run during this manual preparation returned **21 passed**. That fresh terminal result was not written back to the old evidence log. Saved `evidence/tests/frontend_vitest.txt` records 3 passed. Captured lint is clean. Captured production build succeeds but warns that the minified JavaScript bundle is 700.72 kB, exceeding Vite’s 500 kB chunk warning threshold.

**Testing limits:** Frontend tests use a mocked `fetch`, not a browser+live API integration test. Assistant provider tests mock Groq; one real assistant API call did succeed in this workspace on 2026-10-03, but that check is not present in the saved old evidence report. Screenshot files exist as evidence, but `scripts/capture_evidence.py` does not capture screenshots itself. No stress/load, browser automation, production security, external-data validation, drift, calibration, or end-to-end visual regression tests are present in inspected code.

### Evidence files

- Dataset: `data/admission_data.csv`, `data/validation_report.json`, `evidence/dataset/dataset_summary.json`, `evidence/dataset/validation_report.json`.
- Analytics/forecast/scenario: `evidence/metrics/analytics_report.json`, `forecast_report.json`, `scenario_report.json`.
- Models: `evidence/models/model_report.json`, `evidence/models/admitflow_model.joblib`; another bundle exists under `data/models/`.
- API/security: `evidence/api/api_smoke.json`, `evidence/security/auth_check.json`.
- Test/build: `evidence/tests/backend_pytest.txt`, `frontend_vitest.txt`, `frontend_lint.txt`, `frontend_build.txt`.
- Evidence capture: `scripts/capture_evidence.py`; tracker updates: `scripts/generate_tracker.py`, `scripts/finalize_tracker.py`; workbook `TRACKER.xlsx` currently reports 17 tasks completed, but completion labels do not imply production readiness.

## Limitations and future scope

### Current implementation limitations

1. **Synthetic-only data:** No real institution source, governance approval, applicant privacy policy, or real-world representativeness is established.
2. **Small annual history:** Six data points; forecast test set is two years and future fit uses only first four rows.
3. **Weak classifier quality:** AUC near chance; forest positive recall is zero. Do not use models to admit, reject, rank or prioritize applicants.
4. **Potential synthetic process artifacts:** Outcomes are generated by code; models can learn generator patterns that do not transfer.
5. **Descriptive groups only:** Cohorts, programmes, and campaign channels are not adjusted for confounding; no causal attribution.
6. **Scenario assumptions are arithmetic:** No estimated intervention effects, uncertainty or stochastic variation. `campaign_shift` is output metadata, not part of count calculation.
7. **AI risk/dependency:** External provider required; prompt/schema controls reduce but do not eliminate hallucinations. Current model answer quality is not covered by a live repeatable eval set.
8. **Authentication is local-demo quality:** One seeded user, no signup or account lifecycle; browser token localStorage; logout token query parameter.
9. **Audit durability:** Event list resets with process and retains only the last ten on retrieval.
10. **Performance/deployment:** `/api/model` retrains on each page load request; no production deployment manifest or monitoring is present. Frontend bundle warning >500 kB.
11. **Validation gaps:** Stage consistency block is a no-op; only selected conditions are checked.
12. **Project docs are partly stale:** README/final verification still describe JWT secret and previous test count, despite current SQLite sessions and 21-test current run.

### Future scope — not implemented

- Obtain governed, representative institutional data with privacy review and clear outcome definitions.
- Add reliable ingestion, schema versioning, data-quality monitoring and explicit stage/flag consistency rules.
- Evaluate classifiers with temporal/external validation, repeated splits, calibration, threshold/cost analysis, subgroup fairness checks and uncertainty; compare a simple prevalence/majority baseline.
- Refit forecasts on all available history after evaluation; add naïve baseline, more cycles, rolling-origin validation, intervals and relevant exogenous variables if justified.
- Build causal attribution only if a defensible experimental/quasi-experimental design and data become available.
- Add scenario uncertainty and incorporate campaign shifts only after their semantics and estimated effects are defined; otherwise continue labeling them as assumptions.
- Add account creation, password resets, secure credential provisioning, rate limiting, durable audit storage, safe logout handling, and role/permission policy.
- Add integration/UI automation, live-provider evaluation fixtures, model monitoring, drift checks, and privacy-focused AI policy. RAG is a possible future architecture, not current behavior.
- Add a reproducible deployment setup and operational secret management before production.

## Questions about implementation choices

| Examiner asks | Code-grounded response |
|---|---|
| Why FastAPI? | It is the actual backend framework; its route decorators, Pydantic request models, dependency-based bearer check and TestClient support the small local JSON API. The repository does not record a measured framework benchmark. |
| Why SQLite? | Current auth needs one local persistence file for demo user and sessions without introducing an external DB service. Analytics still come from CSV. This is suitable for the local demo, not evidence of production scale. |
| Why pandas? | The implementation reads the tabular CSV and uses `groupby`, `agg`, sums and DataFrame serialization for analytical outputs. |
| Why scikit-learn? | It supplies the implemented preprocessing, split, classifier/regression estimators, evaluation metrics and pipelines. The repo does not document a comparative library study. |
| Why logistic regression? | It is the explicitly named interpretable baseline comparator; `class_weight="balanced"` addresses class proportion during fitting, though measured performance remains weak. |
| Why random forest? | It is the chosen tree-ensemble comparator with 200 trees and leaf size 2. Code does not select it as best; its thresholded recall is zero. |
| Why this forecast? | It is a transparent linear trend over an index. There is no code evidence that other forecast methods were compared. |
| Why Recharts? | It is the declared React chart library used for area, bar, line and composed charts. No documented benchmark against alternatives. |
| Why an LLM? | To answer natural-language questions about aggregates already computed by backend; it does not replace formal analytics or classifier predictions. |
| Why Groq? | Groq SDK is the configured provider client in `assistant.py`; the repository does not document a provider comparison or selection study. |
| Why one-hot encoding? | Nominal categories have no numeric order; one-hot represents categories as indicator features and ignores unseen categories. |
| Why no scaling? | The code does not implement scaling; do not invent a rationale. Acknowledge this and identify numeric scale differences as a possible modeling improvement. |
| Why deterministic scenarios? | Determinism makes assumptions and outputs reproducible. This is a documented design, but not a calibrated estimate of intervention outcomes. |
| Why React state and no router? | The current app is a compact SPA; `page` state selects the views and avoids a routing dependency. Deep links/history-based routes are not implemented. |
| Why these API routes? | They separate analytics outputs by use case and share a bearer-token dependency; no versioned route prefix is used. |

## 25 difficult examiner cross-examination chains

Each chain follows the initial answer with progressively harder follow-ups. Keep the answer truthful and avoid defending weak results as successes.

### Chain 1 — Project purpose
- **Examiner:** What does AdmitFlow solve? **Student:** It turns a synthetic applicant table into funnel, segment, programme, source, forecast, and scenario views.
- **Follow-up:** Does it process real applications? **Student:** No, not in the current repository; it reads the generated CSV.
- **Follow-up:** Then what is the contribution? **Student:** An integrated, inspectable analytics workflow and honest demonstration of method limits, not an operational admission system.

### Chain 2 — Dataset credibility
- **Examiner:** Where did the data come from? **Student:** Repository code generates it with NumPy seed 42.
- **Follow-up:** Does seed 42 make it representative? **Student:** No, it makes generation repeatable, not representative.
- **Follow-up:** Can the results be generalized? **Student:** Not without real, governed data and external validation.

### Chain 3 — Exclusive stage vs funnel
- **Examiner:** Why not count `stage` for the funnel? **Student:** `stage` is one exclusive final-stage label; funnel counts use cumulative flags.
- **Follow-up:** What are the two totals? **Student:** Exclusive lead label 1,094, but lead base is all 4,200; cumulative app starts are 3,106.
- **Follow-up:** What if flags disagree with stage? **Student:** The validator does not comprehensively check that consistency, so results would need data-quality controls.

### Chain 4 — Bottleneck
- **Examiner:** Where is the biggest drop? **Student:** Application started to submitted, 1,123 rows.
- **Follow-up:** What caused it? **Student:** The data only shows the count difference; it does not establish a cause.
- **Follow-up:** What analysis would you need? **Student:** Defined process events, cohort/context controls, qualitative inquiry or a causal design depending on the claim.

### Chain 5 — Rate denominator
- **Examiner:** What is the conversion rate? **Student:** Overall it is 351 enrolled divided by 4,200 lead rows, 8.36%.
- **Follow-up:** Is every stage rate using that denominator? **Student:** `conversion_rate` does; `from_previous_stage` divides by prior stage.
- **Follow-up:** Why does that distinction matter? **Student:** It distinguishes cumulative share from stage-to-stage conversion.

### Chain 6 — Programmes
- **Examiner:** Which programme performs best? **Student:** Computer Science has a 9.04% observed enrolment rate, slightly above AI Engineering at 9.03%.
- **Follow-up:** Is that a meaningful difference? **Student:** No significance or uncertainty test is implemented; it is a tiny descriptive difference.
- **Follow-up:** Would you rank applicants/programmes based on it? **Student:** No; synthetic, unadjusted group rates do not justify that.

### Chain 7 — Attribution
- **Examiner:** Which source causes the most enrolments? **Student:** The code cannot answer causal impact. Social has 65 enrolments and 9.64% observed rate.
- **Follow-up:** Which source has most applications? **Student:** Partner, 749.
- **Follow-up:** Why are those not ROI? **Student:** There is no campaign cost, experimental assignment, or counterfactual analysis.

### Chain 8 — Classifier target
- **Examiner:** What does your ML model predict? **Student:** It classifies the synthetic `enrolled` flag from 12 selected features.
- **Follow-up:** Does the API predict a specific applicant’s chance? **Student:** No; `/api/model` returns holdout metrics and feature signals, not per-applicant scoring.
- **Follow-up:** Could it be used for admissions? **Student:** No; results are weak and the data synthetic.

### Chain 9 — Class imbalance
- **Examiner:** Why is random forest accuracy high? **Student:** 91.62% of holdout rows are negative and the forest predicts all rows negative.
- **Follow-up:** What is its recall? **Student:** Zero; it misses all 88 positives.
- **Follow-up:** What metric would you focus on? **Student:** Recall, precision, average precision/PR-AUC, confusion matrix, and a suitable threshold/cost analysis; none makes this model ready.

### Chain 10 — Baseline vs advanced
- **Examiner:** Which is best? **Student:** The code compares but does not implement a selection criterion. Each metric differs; neither is decision-ready.
- **Follow-up:** Forest has lower log loss. Is that enough? **Student:** No; ranking is near chance and its thresholded positive recall is zero.
- **Follow-up:** What would you add? **Student:** Baselines, repeated/temporal validation, calibration, threshold review, uncertainty and subgroup analysis.

### Chain 11 — Preprocessing
- **Examiner:** Why impute if there are no missing values? **Student:** It makes a pipeline robust to missing inputs; on this CSV the imputers have no missing cells to fill.
- **Follow-up:** Why one-hot encode? **Student:** Categories have no ordinal meaning and the estimators require numeric features.
- **Follow-up:** Did you scale? **Student:** No. Scaling is not implemented and is a possible improvement, especially for logistic optimization.

### Chain 12 — Leakage
- **Examiner:** Is leakage prevented? **Student:** Direct labels/stage/ID are excluded, but a complete leakage audit is not implemented.
- **Follow-up:** Is the split temporal? **Student:** No, classifier split is stratified random 75/25.
- **Follow-up:** What would better reflect deployment? **Student:** A time-based split using older cycles for training and later cycles for testing, with enough cycles and independent validation.

### Chain 13 — Forecast model
- **Examiner:** What model forecasts enrolment? **Student:** LinearRegression over annual enrolled counts and a sequential year index.
- **Follow-up:** Why not call it a seasonal model? **Student:** There are annual aggregates and no seasonal component.
- **Follow-up:** Was it selected against alternatives? **Student:** No comparison is present in `forecast.py`.

### Chain 14 — Forecast training-year bug
- **Examiner:** How many years train the forecast? **Student:** The model fit uses four: 2021–2024; 2025–2026 are held out.
- **Follow-up:** Why does the API say six? **Student:** `training_years` is set to total series length, six, not fit length.
- **Follow-up:** What fix is needed? **Student:** Report fit length accurately and refit on all six years for future prediction after holdout evaluation.

### Chain 15 — Forecast error
- **Examiner:** What does MAPE 0.2733 mean? **Student:** About 27.33% mean absolute relative error on two nonzero holdout years.
- **Follow-up:** Is that stable? **Student:** No, two observations are too few to estimate stable performance.
- **Follow-up:** What would you communicate? **Student:** Directional illustration only; add more cycles, rolling evaluation, a baseline and prediction intervals.

### Chain 16 — Scenario
- **Examiner:** Is the Scenario Lab an ML model? **Student:** No, it is deterministic scaling, multiplication, rounding and clamping.
- **Follow-up:** Where do multipliers come from? **Student:** User-entered assumptions/presets, not learned effects.
- **Follow-up:** Can we promise 435 enrolments? **Student:** No, it is the arithmetic output under those assumptions, not an outcome guarantee.

### Chain 17 — Campaign shift
- **Examiner:** How does campaign shift affect the scenario? **Student:** It currently does not affect counts; the object is returned as metadata.
- **Follow-up:** Why is it there? **Student:** It appears as an optional input/default in the engine/API, but there is no active calculation using it.
- **Follow-up:** What should you say in the viva? **Student:** It is a current implementation gap, not a functioning campaign response model.

### Chain 18 — AI grounding
- **Examiner:** How does the LLM get the data? **Student:** The FastAPI route computes aggregates and includes them in the prompt JSON.
- **Follow-up:** Is this RAG? **Student:** No, no retriever or vector store exists.
- **Follow-up:** Can it hallucinate? **Student:** Yes; prompt instructions and schema validation reduce format/grounding risk but cannot guarantee factuality.

### Chain 19 — AI vs ML
- **Examiner:** Does Groq make your prediction? **Student:** No, sklearn does classifiers and linear forecast; Groq turns supplied aggregates into a natural-language answer.
- **Follow-up:** Why use both? **Student:** They serve separate interfaces/tasks: numeric calculations and natural-language exploration.
- **Follow-up:** What if Groq is down? **Student:** AI route returns a provider error; analytics remain available.

### Chain 20 — Privacy
- **Examiner:** Are applicant records sent to the provider? **Student:** The route sends selected aggregates, not row-level applicant records.
- **Follow-up:** Is that sufficient for production privacy? **Student:** Not by itself; data governance and provider terms still need review.
- **Follow-up:** Where is the key? **Student:** Backend environment/root `.env`; it must never enter frontend code or this document.

### Chain 21 — Database
- **Examiner:** What does SQLite store? **Student:** A seeded user with password hash/salt and sessions with token hashes and expiry.
- **Follow-up:** Does it store analytics data? **Student:** No; analytics load from CSV.
- **Follow-up:** Can I register? **Student:** No registration endpoint exists; only the demo user is provisioned.

### Chain 22 — Token security
- **Examiner:** What is stored as a session token? **Student:** A random URL-safe token is returned; only SHA-256 digest is stored in SQLite.
- **Follow-up:** How long does it last? **Student:** Eight hours; logout deletes it.
- **Follow-up:** What is a weakness? **Student:** Browser token is in localStorage and logout passes it in a query string; production auth should improve both.

### Chain 23 — Audit
- **Examiner:** Is audit history durable? **Student:** No, it is an in-memory Python list and only last ten are returned.
- **Follow-up:** Which events are logged? **Student:** Successful login/logout, scenario run, assistant success.
- **Follow-up:** What is future scope? **Student:** Durable append-only storage, stronger event coverage and retention/access controls.

### Chain 24 — Validation
- **Examiner:** What does data validation guarantee? **Student:** It reports selected checks, not total data correctness.
- **Follow-up:** Does it verify monotonic flags? **Student:** Not comprehensively; the stage-rank code is a no-op.
- **Follow-up:** What would you add? **Student:** Binary-domain, flag nesting, stage-flag, cycle-date and complete schema consistency checks.

### Chain 25 — Production readiness
- **Examiner:** Is the project production-ready? **Student:** No; it is a locally verified capstone on synthetic data.
- **Follow-up:** Give three blockers. **Student:** Synthetic data, weak model/short forecast evidence, and demo-grade identity/audit/deployment controls.
- **Follow-up:** What must happen before use? **Student:** Governed real data, independent validation and a security/operations review; keep decisions human-led and auditable.

## Complete spoken explanation: 16-part outline

Use these as connected talking points for a longer viva answer. Keep the same claims as the timed pitches above.

1. **Introduction:** “My project is AdmitFlow, titled ‘Admission Conversion Forecasting with Funnel Attribution and Scenario Simulation.’ It is a local analytics and decision-support prototype.”
2. **Problem:** “Applicant records need to be summarized to see stage movement and compare observed groups. A chart alone does not explain causes.”
3. **Objective:** “I connect reproducible synthetic data, validation, descriptive analytics, exploratory models, a short trend forecast, and controlled arithmetic scenarios in one application.”
4. **Dataset:** “The generator uses seed 42 to create 4,200 records across 2021–2026. It is synthetic, and there is no identified external source.”
5. **Methodology:** “I validate selected domains and missingness, aggregate with pandas, encode/impute features in sklearn pipelines, use a stratified holdout for classifiers, and chronological holdout for the annual trend.”
6. **Architecture:** “React/Vite calls JSON routes in FastAPI. The API reads the CSV and invokes analytics functions. Authentication persistence is separate SQLite; audit remains process-local.”
7. **ML:** “I compare logistic regression with a random forest on the `enrolled` flag and report threshold-independent and thresholded metrics. Neither is good enough for applicant decisions.”
8. **Forecasting:** “I aggregate annual enrolments and fit linear regression against year index. Six annual observations exist; the code trains on first four, tests last two, then extrapolates the same model.”
9. **Scenario simulation:** “I scale baseline counts to requested volume, apply stage multipliers, round and clamp to keep counts monotonic. The output is deterministic and assumption-driven.”
10. **Attribution:** “I group recorded source labels and calculate shares and observed rates. The results are descriptive and do not prove campaign effects.”
11. **AI:** “The route sends the question with computed aggregate context to a Groq model. It is prompt context injection, not RAG, and not the numeric ML engine.”
12. **Dashboard:** “The React SPA loads 11 data responses, stores them in component state, and displays tables, charts, filters, dialogs, responsive navigation and errors.”
13. **Results:** “The overall synthetic lead-to-enrolled rate is 8.36%; source and programme differences are descriptive; classifier discrimination is weak; forecast errors are large relative to the small evaluation set.”
14. **Limitations:** “Synthetic data, one random classifier split, no forecast uncertainty, deterministic scenario assumptions, local-only demo identity, and non-durable audit are key limitations.”
15. **Future scope:** “Use approved institutional data, strengthen validation, run temporal and subgroup model evaluation, refit and quantify forecast uncertainty, implement real account lifecycle and durable audits.”
16. **Conclusion:** “The project demonstrates transparent analytics and communicates uncertainty; it does not claim causal effects or operational predictive validity.”

## Live demonstration script

Do not spend the viva waiting on model retraining or an external LLM. Sign in first and keep a fallback explanation ready. The project runs locally with the frontend at port 5173 and FastAPI at port 8000 when both development processes are running.

| Step | What to click/show | What to say | Concept demonstrated | Likely examiner question |
|---|---|---|---|---|
| 1. Login | Login page; use demo access. | “This is local demo authentication; there is no registration flow.” | API login and bearer token | “Can I create an account?” No, not in current UI/API. |
| 2. Dashboard | Point to totals, cycle, funnel and forecast preview. | “All numbers come from the current CSV aggregates.” | Fetch/state/dashboard metrics | “Is this real data?” No, synthetic. |
| 3. Funnel | Show six stages and largest loss; open detailed table. | “The 1,123 drop is application-start to submitted; it says where, not why.” | Cumulative flags and transition rates | “Does it explain abandonment?” No causal variable is analyzed. |
| 4. Cohorts | Switch cycle, programme, region, selectivity and source. | “These are unadjusted group rates, with a code threshold label at 80.” | groupby and denominators | “Are differences significant?” No tests are implemented. |
| 5. Programmes | Sort/filter; open Computer Science/AI Engineering drawer. | “The drawer trend is annual applications; totals are grouped flags.” | Grouped metrics and detail component | “Why does one differ?” The code does not establish why. |
| 6. Attribution | Compare source share and observed enrolment rates. | “Partner has most rows; Social has highest current rate; neither is causal or ROI.” | Descriptive attribution | “Did social cause it?” No. |
| 7. Forecast | Point to historical/forecast boundary, horizons and errors. | “Linear trend; six observations, first four fit, last two holdout; current code reuses the first-four fit.” | Regression, holdout, uncertainty | “What is H4?” Projection four cycles after 2026: 2030, 83.5. |
| 8. Scenario | Select Expected, inspect multipliers, Run scenario. | “5,000 scaled applications yields 2,479 submitted, 910 admitted, 435 enrolled by the formula.” | Deterministic simulation | “Is this predicted?” No; it is deterministic assumptions. |
| 9. Model | Show logistic vs forest metrics and feature selector. | “Forest predicts no positive holdout rows at threshold, so accuracy is misleading.” | Imbalance, PR metrics, feature signals | “Which model should be deployed?” Neither. |
| 10. AI assistant | Ask “Which source has the most applications?” if provider is configured; show citations. | “Backend computes aggregate context; the provider returns structured JSON; this is not RAG.” | External LLM integration | “What happens if provider fails?” UI error; analytics still work. |
| 11. Audit | Show current process events and filters. | “This list is in memory and resets on API restart.” | Event logging limits | “Is this a compliance log?” No. |
| 12. Settings/search/theme | Toggle theme, open settings, press Ctrl/Cmd+K and search a page/metric. | “Theme/sidebar persist in browser; command palette filters already-loaded data.” | client state/localStorage/search | “Does search query the server?” No. |

### Efficient 7-minute demo order

1. Login and dashboard (45 seconds).
2. Funnel, then cohorts and programme table (90 seconds).
3. Attribution with causal distinction (45 seconds).
4. Forecast with explicit four-fit/two-holdout nuance (75 seconds).
5. Expected scenario and hand calculation (75 seconds).
6. Model metrics and why accuracy fails (75 seconds).
7. AI only if provider is available; otherwise show offline behavior (45 seconds).
8. Audit, settings/theme, and close with limitations (45 seconds).

If the external AI service is unavailable, do not debug live; show the UI’s offline state and explain the mocked-provider tests. If the backend model endpoint is slow, use already-loaded dashboard state and saved evidence reports rather than waiting.

## 100-question viva bank

Each entry has a question, a speakable answer, key points and an examiner follow-up. Answers intentionally favor accuracy over overselling.

### A. Basic project questions

**A1. QUESTION:** What is AdmitFlow?  
**IDEAL ANSWER:** A local admission analytics and decision-support prototype using a generated synthetic dataset.  
**KEY POINTS:** Funnel, comparisons, models, forecast, scenarios, optional LLM.  
**LIKELY FOLLOW-UP:** Is it a production admissions system?

**A2. QUESTION:** What is the official topic title?  
**IDEAL ANSWER:** “Admission Conversion Forecasting with Funnel Attribution and Scenario Simulation.”  
**KEY POINTS:** Exact title in `docs/PROJECT_SPEC.md`.  
**LIKELY FOLLOW-UP:** Why include scenario simulation?

**A3. QUESTION:** Who is the intended user?  
**IDEAL ANSWER:** Local evaluators and admissions/enrolment teams reviewing aggregate outcomes.  
**KEY POINTS:** Product scope is analytics/decision support, not applicant processing.  
**LIKELY FOLLOW-UP:** Did a real institution validate it?

**A4. QUESTION:** What are the main capabilities?  
**IDEAL ANSWER:** Funnel, cohorts, programmes, source attribution, classifier comparison, forecast, deterministic scenarios and aggregate-context assistant.  
**KEY POINTS:** All shown in React and exposed by FastAPI.  
**LIKELY FOLLOW-UP:** Which one is causal?

**A5. QUESTION:** What is your one-sentence conclusion?  
**IDEAL ANSWER:** It demonstrates an auditable local analytics workflow on synthetic data, but the models and forecast are not operationally validated.  
**KEY POINTS:** State evidence and limitation together.  
**LIKELY FOLLOW-UP:** What is the strongest result?

### B. Problem statement

**B1. QUESTION:** What admission problem do you address?  
**IDEAL ANSWER:** Difficulty seeing how records move through stages and how aggregate outcomes vary across groups.  
**KEY POINTS:** Project spec describes funnel visibility and planning.  
**LIKELY FOLLOW-UP:** Does your app process applications?

**B2. QUESTION:** Why is raw CSV insufficient?  
**IDEAL ANSWER:** Rows do not directly show grouped counts, rates, losses, or future assumptions; the backend computes these summaries.  
**KEY POINTS:** CSV remains source.  
**LIKELY FOLLOW-UP:** Why not put metrics in the frontend?

**B3. QUESTION:** What is the core objective?  
**IDEAL ANSWER:** Connect data generation/validation, descriptive analytics, exploratory modeling and planning views with explicit caveats.  
**KEY POINTS:** Project spec/objectives.  
**LIKELY FOLLOW-UP:** What objective is not met fully?

**B4. QUESTION:** What is decision support here?  
**IDEAL ANSWER:** A human can inspect aggregates and test assumptions; the app does not automate admissions decisions.  
**KEY POINTS:** No applicant-level prediction endpoint.  
**LIKELY FOLLOW-UP:** Could the model rank applicants?

**B5. QUESTION:** What is the expected outcome?  
**IDEAL ANSWER:** Demonstrate analysis and planning calculations that users can inspect, not guarantee enrollment growth.  
**KEY POINTS:** Avoid business impact claims.  
**LIKELY FOLLOW-UP:** How would impact be measured?

### C. Data Science

**C1. QUESTION:** Why is this Data Science?  
**IDEAL ANSWER:** It validates and aggregates data, fits supervised models, evaluates a regression forecast, and interprets limitations.  
**KEY POINTS:** `data_generator.py`, `analytics.py`, `ml.py`, `forecast.py`.  
**LIKELY FOLLOW-UP:** Which output is not ML?

**C2. QUESTION:** Distinguish prediction, forecast, attribution and causation.  
**IDEAL ANSWER:** Prediction estimates a labeled outcome, forecast extrapolates a time series, attribution groups outcomes by source, and causation estimates intervention effects.  
**KEY POINTS:** Only first three types are represented; attribution is descriptive.  
**LIKELY FOLLOW-UP:** Which component is deterministic?

**C3. QUESTION:** What is exploratory modeling?  
**IDEAL ANSWER:** A pipeline that demonstrates model fitting/metrics without evidence adequate for operational deployment.  
**KEY POINTS:** Weak AUC and synthetic data.  
**LIKELY FOLLOW-UP:** What would make it decision-ready?

**C4. QUESTION:** Is there feature engineering?  
**IDEAL ANSWER:** Limited transformation: selected fields, one-hot categories, imputers, and a year index for forecasting.  
**KEY POINTS:** No elaborate derived applicant features.  
**LIKELY FOLLOW-UP:** Is there normalization?

**C5. QUESTION:** What is the role of interpretation?  
**IDEAL ANSWER:** Explain what an aggregate/model metric says and what it cannot establish.  
**KEY POINTS:** Feature signals are not causal.  
**LIKELY FOLLOW-UP:** Can a top feature be treated as an intervention?

### D. Dataset

**D1. QUESTION:** How many rows and columns?  
**IDEAL ANSWER:** 4,200 rows and 22 columns.  
**KEY POINTS:** CSV and validation report.  
**LIKELY FOLLOW-UP:** Are rows real applicants?

**D2. QUESTION:** What is the source?  
**IDEAL ANSWER:** `data_generator.py`; no external source is documented.  
**KEY POINTS:** Synthetic seed 42.  
**LIKELY FOLLOW-UP:** What does reproducibility mean here?

**D3. QUESTION:** What cycles are covered?  
**IDEAL ANSWER:** 2021 to 2026 inclusive, six annual cycles.  
**KEY POINTS:** Counts 684, 708, 708, 692, 712, 696.  
**LIKELY FOLLOW-UP:** Is six enough for forecasting?

**D4. QUESTION:** What is the target and class balance?  
**IDEAL ANSWER:** `enrolled`; 351 positives out of 4,200, 8.36%.  
**KEY POINTS:** Binary integer flag.  
**LIKELY FOLLOW-UP:** What metric issue follows?

**D5. QUESTION:** What are the key categorical variables?  
**IDEAL ANSWER:** Programme, selectivity, region, campaign source, and exclusive stage; campaign code is also text-like.  
**KEY POINTS:** 5, 3, 5, 6 categories respectively for modeled categories.  
**LIKELY FOLLOW-UP:** Which categorical fields enter ML?

### E. Preprocessing

**E1. QUESTION:** How are missing values handled?  
**IDEAL ANSWER:** Model pipeline imputes numeric medians and categorical modes; the current CSV has no missing values.  
**KEY POINTS:** Imputers fit within pipeline.  
**LIKELY FOLLOW-UP:** Does analytics use those imputers?

**E2. QUESTION:** How are categories encoded?  
**IDEAL ANSWER:** One-hot encoding with unknown categories ignored.  
**KEY POINTS:** Inside `ColumnTransformer`.  
**LIKELY FOLLOW-UP:** Why not ordinal encoding?

**E3. QUESTION:** Is scaling performed?  
**IDEAL ANSWER:** No scaler or normalization is in `ml.py`.  
**KEY POINTS:** Do not state otherwise.  
**LIKELY FOLLOW-UP:** What effect might that have?

**E4. QUESTION:** How are duplicates checked?  
**IDEAL ANSWER:** Duplicate `applicant_id` count, not full-row duplicate count.  
**KEY POINTS:** Current count zero.  
**LIKELY FOLLOW-UP:** Does the validator remove duplicates?

**E5. QUESTION:** Is the data cleaned?  
**IDEAL ANSWER:** Validation reports selected issues but does not mutate/clean the frame.  
**KEY POINTS:** No missing values in current generated CSV.  
**LIKELY FOLLOW-UP:** Does the API validate every read?

### F. Machine Learning

**F1. QUESTION:** Which models are implemented?  
**IDEAL ANSWER:** LogisticRegression and RandomForestClassifier for binary `enrolled`.  
**KEY POINTS:** sklearn pipelines.  
**LIKELY FOLLOW-UP:** Which is selected automatically?

**F2. QUESTION:** What features enter the classifiers?  
**IDEAL ANSWER:** Four categorical and eight numeric fields, including cycle year and engagement/academic indicators.  
**KEY POINTS:** Exact list in `FEATURES` / manual.  
**LIKELY FOLLOW-UP:** Why exclude stage?

**F3. QUESTION:** What is the split?  
**IDEAL ANSWER:** Stratified random 75/25, `random_state=42`.  
**KEY POINTS:** Not temporal CV.  
**LIKELY FOLLOW-UP:** What deployment risk remains?

**F4. QUESTION:** What is the random forest configuration?  
**IDEAL ANSWER:** 200 trees, minimum leaf size 2, seed 42.  
**KEY POINTS:** Other settings are sklearn defaults.  
**LIKELY FOLLOW-UP:** Does that guarantee robustness?

**F5. QUESTION:** Does the model score a new applicant?  
**IDEAL ANSWER:** No route accepts an applicant record for prediction; `/api/model` retrains/reports holdout metrics.  
**KEY POINTS:** No deployment inference endpoint.  
**LIKELY FOLLOW-UP:** What does the saved joblib contain?

### G. Metrics

**G1. QUESTION:** Why is forest accuracy misleading?  
**IDEAL ANSWER:** It predicts all holdout records negative, so majority negatives create 91.62% accuracy despite zero recall.  
**KEY POINTS:** Confusion matrix.  
**LIKELY FOLLOW-UP:** Which matrix cell is zero?

**G2. QUESTION:** What does precision measure?  
**IDEAL ANSWER:** Among predicted positives, the fraction truly positive.  
**KEY POINTS:** Baseline 10.28%, forest zero.  
**LIKELY FOLLOW-UP:** What does low precision imply?

**G3. QUESTION:** What does recall measure?  
**IDEAL ANSWER:** Among actual enrolled cases, the fraction found.  
**KEY POINTS:** Baseline 46.59%, forest zero.  
**LIKELY FOLLOW-UP:** Which errors are false negatives?

**G4. QUESTION:** Why include ROC-AUC and PR-AUC?  
**IDEAL ANSWER:** They summarize ranking across thresholds; average precision focuses more on positive-class precision/recall under imbalance.  
**KEY POINTS:** Near-chance ROC-AUC.  
**LIKELY FOLLOW-UP:** What is the no-skill PR reference?

**G5. QUESTION:** What does forecast MAPE mean?  
**IDEAL ANSWER:** 0.2733 means 27.33% average absolute relative error across the two nonzero holdout years.  
**KEY POINTS:** Stored as fraction, UI formats percentage.  
**LIKELY FOLLOW-UP:** What if actual is zero?

### H. Forecasting

**H1. QUESTION:** What is forecast target?  
**IDEAL ANSWER:** Annual sum of the `enrolled` flag by cycle.  
**KEY POINTS:** Other annual sums are returned but not predicted.  
**LIKELY FOLLOW-UP:** What is input feature?

**H2. QUESTION:** What method is used?  
**IDEAL ANSWER:** sklearn LinearRegression against a sequential year index.  
**KEY POINTS:** Straight-line trend.  
**LIKELY FOLLOW-UP:** Is it ARIMA?

**H3. QUESTION:** What does H4 mean?  
**IDEAL ANSWER:** Four years beyond last cycle 2026: year 2030, forecast 83.5.  
**KEY POINTS:** H1/H2/H4/H6.  
**LIKELY FOLLOW-UP:** Why is H3 not shown?

**H4. QUESTION:** How many observations fit the current model?  
**IDEAL ANSWER:** Four, years 2021–2024; 2025–2026 are holdout.  
**KEY POINTS:** `training_years` response incorrectly says six.  
**LIKELY FOLLOW-UP:** What should be fixed?

**H5. QUESTION:** Why are results directional?  
**IDEAL ANSWER:** Six annual points, two test points, synthetic records, no intervals, and a simple linear form.  
**KEY POINTS:** Not operational.  
**LIKELY FOLLOW-UP:** What evaluation would improve confidence?

### I. Scenario simulation

**I1. QUESTION:** What is the scenario input?  
**IDEAL ANSWER:** Requested application volume and submitted/admitted/enrolled multipliers.  
**KEY POINTS:** Frontend presets and sliders.  
**LIKELY FOLLOW-UP:** Are multipliers learned?

**I2. QUESTION:** What is the calculation type?  
**IDEAL ANSWER:** Deterministic rule-based arithmetic with scaling, rounding and clamps.  
**KEY POINTS:** `deterministic: true`.  
**LIKELY FOLLOW-UP:** Is it a prediction?

**I3. QUESTION:** Why clamp?  
**IDEAL ANSWER:** To preserve nonnegative monotonic stage counts even when assumptions imply later stage above prior stage.  
**KEY POINTS:** Submitted ≤ applications, admitted ≤ submitted, enrolled ≤ admitted.  
**LIKELY FOLLOW-UP:** Does it explain conversion?

**I4. QUESTION:** What does Expected preset produce?  
**IDEAL ANSWER:** At 5,000 applications: 2,479 submitted, 910 admitted, 435 enrolled.  
**KEY POINTS:** Default factors 1.05/1.08/1.04.  
**LIKELY FOLLOW-UP:** Is 435 guaranteed?

**I5. QUESTION:** Does campaign shift change totals?  
**IDEAL ANSWER:** No. It is returned as metadata but not applied to scenario calculations.  
**KEY POINTS:** No campaign control in UI.  
**LIKELY FOLLOW-UP:** Is that a limitation?

### J. Attribution

**J1. QUESTION:** What source categories exist?  
**IDEAL ANSWER:** Search, Referral, Social, Partner, Event, Direct.  
**KEY POINTS:** Generator and current report.  
**LIKELY FOLLOW-UP:** Which has most applications?

**J2. QUESTION:** What does source share mean?  
**IDEAL ANSWER:** Rows assigned to a source divided by all applicant/application rows.  
**KEY POINTS:** Partner 17.83%.  
**LIKELY FOLLOW-UP:** Does it include spend?

**J3. QUESTION:** Which source has highest enrolment rate?  
**IDEAL ANSWER:** Social, 65/674 = 9.64% in saved synthetic report.  
**KEY POINTS:** Partner has most application volume.  
**LIKELY FOLLOW-UP:** Does that prove campaign effectiveness?

**J4. QUESTION:** What is causal attribution?  
**IDEAL ANSWER:** Estimating the outcome difference caused by a treatment relative to a defensible counterfactual.  
**KEY POINTS:** Not implemented.  
**LIKELY FOLLOW-UP:** What design might support it?

**J5. QUESTION:** Why include a disclaimer?  
**IDEAL ANSWER:** Grouped association can be confounded and should not be presented as intervention effect.  
**KEY POINTS:** Backend literal note and UI disclaimer.  
**LIKELY FOLLOW-UP:** Is source randomized?

### K. AI

**K1. QUESTION:** What provider/model is used?  
**IDEAL ANSWER:** Groq SDK, default model string `openai/gpt-oss-120b`, configurable by `ADMITFLOW_AI_MODEL`.  
**KEY POINTS:** Server-side call.  
**LIKELY FOLLOW-UP:** Is model fixed?

**K2. QUESTION:** What context reaches the LLM?  
**IDEAL ANSWER:** Aggregated dashboard, funnel, programme, source, cohorts, forecast and optional scenario.  
**KEY POINTS:** No applicant rows.  
**LIKELY FOLLOW-UP:** Is it RAG?

**K3. QUESTION:** How is output validated?  
**IDEAL ANSWER:** JSON-object response mode and Pydantic `AssistantAnswer` validation.  
**KEY POINTS:** answer, data_used, up to three follow-ups.  
**LIKELY FOLLOW-UP:** Does schema validation prevent factual hallucination?

**K4. QUESTION:** What if the key is missing?  
**IDEAL ANSWER:** Status reports unconfigured and the assistant endpoint returns 503; analytics still work.  
**KEY POINTS:** UI disables sending.  
**LIKELY FOLLOW-UP:** Does status prove key is valid?

**K5. QUESTION:** Is there streaming?  
**IDEAL ANSWER:** No; one completion is awaited and returned as JSON.  
**KEY POINTS:** no stream mode in `assistant.py`.  
**LIKELY FOLLOW-UP:** What provider errors occur?

### L. Backend

**L1. QUESTION:** What framework and entry point?  
**IDEAL ANSWER:** FastAPI app in `backend/admitflow/server.py`; Uvicorn runs it.  
**KEY POINTS:** main.py alternative entry.  
**LIKELY FOLLOW-UP:** Does the API use version prefix?

**L2. QUESTION:** How is data loaded?  
**IDEAL ANSWER:** `load_dataset()` reads configured CSV with pandas on each request.  
**KEY POINTS:** No cache.  
**LIKELY FOLLOW-UP:** What is the performance implication?

**L3. QUESTION:** How are requests validated?  
**IDEAL ANSWER:** Pydantic models constrain assistant question and scenario volume; multiplier dictionaries are generic.  
**KEY POINTS:** FastAPI 422 on validation failure.  
**LIKELY FOLLOW-UP:** Are multiplier ranges enforced server-side?

**L4. QUESTION:** Which route retrains models?  
**IDEAL ANSWER:** `GET /api/model` calls `train_model()` each time.  
**KEY POINTS:** Not a cached prediction service.  
**LIKELY FOLLOW-UP:** Why might that be slow?

**L5. QUESTION:** What does CORS allow?  
**IDEAL ANSWER:** Two local origins, all methods/headers, credentials false.  
**KEY POINTS:** 5173 on localhost/127.0.0.1.  
**LIKELY FOLLOW-UP:** Is this a production CORS policy?

### M. Frontend

**M1. QUESTION:** What frontend framework?  
**IDEAL ANSWER:** React 19 with Vite; JavaScript/JSX, not TypeScript.  
**KEY POINTS:** `main.jsx`, `App.jsx`.  
**LIKELY FOLLOW-UP:** What handles charts?

**M2. QUESTION:** Is there client-side routing?  
**IDEAL ANSWER:** No routing library; `page` state conditionally renders a component.  
**KEY POINTS:** View navigation doesn't change URL.  
**LIKELY FOLLOW-UP:** What happens on refresh?

**M3. QUESTION:** How many initial requests?  
**IDEAL ANSWER:** Eleven requests inside `Promise.all`.  
**KEY POINTS:** Dashboard, funnel, cohorts, programmes, attribution, forecast, scenarios, model, audit, cycle, assistant status.  
**LIKELY FOLLOW-UP:** What if one fails?

**M4. QUESTION:** Which chart library?  
**IDEAL ANSWER:** Recharts.  
**KEY POINTS:** Responsive charts and custom CSS funnel.  
**LIKELY FOLLOW-UP:** Is the funnel itself Recharts?

**M5. QUESTION:** What does command search do?  
**IDEAL ANSWER:** Ctrl/Cmd+K opens a client-side substring search over pages, loaded programme names and several metrics.  
**KEY POINTS:** At most nine results.  
**LIKELY FOLLOW-UP:** Does it query the API?

### N. Database

**N1. QUESTION:** What database does the project use?  
**IDEAL ANSWER:** SQLite for local auth; CSV for applicant analytics data.  
**KEY POINTS:** Do not say all data is in SQLite.  
**LIKELY FOLLOW-UP:** Is there an ORM?

**N2. QUESTION:** What tables exist?  
**IDEAL ANSWER:** `users` and `sessions`.  
**KEY POINTS:** Columns/constraints in schema section.  
**LIKELY FOLLOW-UP:** Which foreign key?

**N3. QUESTION:** Are passwords stored in plaintext?  
**IDEAL ANSWER:** No; salted PBKDF2-HMAC-SHA256 hashes are stored.  
**KEY POINTS:** 310,000 iterations, 16-byte salt.  
**LIKELY FOLLOW-UP:** Does the DB store raw session tokens?

**N4. QUESTION:** How does session persistence work?  
**IDEAL ANSWER:** Random bearer token is returned; its SHA-256 hash and expiry are stored, so backend restarts do not invalidate it.  
**KEY POINTS:** Eight-hour lifetime.  
**LIKELY FOLLOW-UP:** Is there a signup flow?

**N5. QUESTION:** Are migrations used?  
**IDEAL ANSWER:** No migration framework; tables are created with `IF NOT EXISTS`.  
**KEY POINTS:** Simple local schema.  
**LIKELY FOLLOW-UP:** How to evolve schema safely?

### O. Security

**O1. QUESTION:** How are API routes protected?  
**IDEAL ANSWER:** HTTP bearer dependency validates session token for `/api/*`.  
**KEY POINTS:** Missing/invalid returns 401.  
**LIKELY FOLLOW-UP:** Are roles enforced?

**O2. QUESTION:** Where does the AI key live?  
**IDEAL ANSWER:** Backend process environment or ignored root `.env`, never frontend.  
**KEY POINTS:** Do not show secret.  
**LIKELY FOLLOW-UP:** Does status validate it?

**O3. QUESTION:** What security weakness would you prioritize?  
**IDEAL ANSWER:** Add complete account lifecycle and improve token storage/logout transport; current system is demo-only.  
**KEY POINTS:** LocalStorage and token query.  
**LIKELY FOLLOW-UP:** What else before production?

**O4. QUESTION:** Is OAuth implemented?  
**IDEAL ANSWER:** No; `/auth/oauth` says false and returns no providers.  
**KEY POINTS:** Route is status-only.  
**LIKELY FOLLOW-UP:** Does “OAuth-ready” mean available?

**O5. QUESTION:** How does SQL injection risk get reduced?  
**IDEAL ANSWER:** Auth values use SQLite placeholders rather than string interpolation.  
**KEY POINTS:** Only local auth SQL.  
**LIKELY FOLLOW-UP:** Is that a complete security review?

### P. Testing

**P1. QUESTION:** What backend test framework?  
**IDEAL ANSWER:** pytest with FastAPI TestClient for routes.  
**KEY POINTS:** Eight test files.  
**LIKELY FOLLOW-UP:** What was latest run?

**P2. QUESTION:** What frontend tests exist?  
**IDEAL ANSWER:** Vitest, jsdom and Testing Library; three tests in one App test file.  
**KEY POINTS:** Interactions use mocked fetch.  
**LIKELY FOLLOW-UP:** Are they browser end-to-end tests?

**P3. QUESTION:** What does the ML test prove?  
**IDEAL ANSWER:** Both estimators fit and return expected metric/top-feature keys.  
**KEY POINTS:** Not that predictive quality is good.  
**LIKELY FOLLOW-UP:** How do we assess quality?

**P4. QUESTION:** What evidence is stale?  
**IDEAL ANSWER:** Saved backend log says 20 passed; current auth suite run after changes returned 21, but that run was not saved in the old log.  
**KEY POINTS:** Distinguish runs.  
**LIKELY FOLLOW-UP:** Which count should you report?

**P5. QUESTION:** What tests are missing?  
**IDEAL ANSWER:** Temporal/repeated model validation, live browser/API end-to-end, load, drift and security penetration tests.  
**KEY POINTS:** State as gaps, not completed coverage.  
**LIKELY FOLLOW-UP:** Which is most important?

### Q. Architecture

**Q1. QUESTION:** Describe the request flow.  
**IDEAL ANSWER:** React fetches JSON from FastAPI; backend reads CSV, calls analytical/model code and returns JSON; SQLite is used only for auth.  
**KEY POINTS:** Bearer header.  
**LIKELY FOLLOW-UP:** Where is audit stored?

**Q2. QUESTION:** Is the app microservices-based?  
**IDEAL ANSWER:** No, one FastAPI app with modular Python files plus one React SPA.  
**KEY POINTS:** Local layered architecture.  
**LIKELY FOLLOW-UP:** What are service boundaries?

**Q3. QUESTION:** Is analytics cached?  
**IDEAL ANSWER:** No, CSV is read per endpoint call; frontend requests many endpoints at startup.  
**KEY POINTS:** Model is retrained on startup load via route.  
**LIKELY FOLLOW-UP:** What could improve latency?

**Q4. QUESTION:** What persistent artifacts exist?  
**IDEAL ANSWER:** CSV, JSON evidence/reports, joblib model bundles, SQLite auth file.  
**KEY POINTS:** Audit is not persistent.  
**LIKELY FOLLOW-UP:** Which are ignored by Git?

**Q5. QUESTION:** Is deployment configured?  
**IDEAL ANSWER:** No Docker/compose/cloud deployment manifest was found; README documents local commands.  
**KEY POINTS:** Uvicorn/ Vite local.  
**LIKELY FOLLOW-UP:** What operations work remains?

### R. Limitations

**R1. QUESTION:** What is the biggest data limitation?  
**IDEAL ANSWER:** All records are generated; no institution source or external validation.  
**KEY POINTS:** Seed makes repeatable, not representative.  
**LIKELY FOLLOW-UP:** How to address it?

**R2. QUESTION:** Why are the classifiers weak?  
**IDEAL ANSWER:** The saved holdout shows near-chance ranking and weak positive detection; the synthetic process/features do not yield useful measured discrimination.  
**KEY POINTS:** Avoid inventing a definitive cause.  
**LIKELY FOLLOW-UP:** Would adding features guarantee improvement?

**R3. QUESTION:** What is a forecast limitation?  
**IDEAL ANSWER:** Six annual observations and only four fit points make extrapolation fragile.  
**KEY POINTS:** No intervals.  
**LIKELY FOLLOW-UP:** Does H6 get more certain?

**R4. QUESTION:** What is an attribution limitation?  
**IDEAL ANSWER:** Observed source grouping has no causal design or campaign spend.  
**KEY POINTS:** Confounding and selection.  
**LIKELY FOLLOW-UP:** Can source ranking set budget?

**R5. QUESTION:** What is a system limitation?  
**IDEAL ANSWER:** Demo-only identity, in-memory audit, repeated model training, no production deployment config.  
**KEY POINTS:** Multiple.  
**LIKELY FOLLOW-UP:** What would be first to harden?

### S. Future scope

**S1. QUESTION:** What is your first data improvement?  
**IDEAL ANSWER:** Obtain governed real records with documented outcome definitions and permissions.  
**KEY POINTS:** Privacy and provenance.  
**LIKELY FOLLOW-UP:** How will you evaluate model transfer?

**S2. QUESTION:** How would you improve model evidence?  
**IDEAL ANSWER:** Temporal and external holdouts, cross-cycle stability, class metrics, calibration, threshold/cost and subgroup audits.  
**KEY POINTS:** Only after suitable data.  
**LIKELY FOLLOW-UP:** How avoid overfitting selection?

**S3. QUESTION:** How would you improve forecasting?  
**IDEAL ANSWER:** Refit on all history after holdout evaluation, add more cycles, compare baselines, rolling-origin tests and uncertainty intervals.  
**KEY POINTS:** Fix fit-year field.  
**LIKELY FOLLOW-UP:** Would you add a complex model first?

**S4. QUESTION:** How would you improve auth?  
**IDEAL ANSWER:** Registration and recovery, secure secret provisioning, rate limits, safer token transport/storage, durable audit and role policy.  
**KEY POINTS:** Production identity.  
**LIKELY FOLLOW-UP:** Which features exist now?

**S5. QUESTION:** Would you add RAG?  
**IDEAL ANSWER:** Only if a document corpus or retrieval need exists; current assistant uses structured aggregates directly.  
**KEY POINTS:** RAG is future option.  
**LIKELY FOLLOW-UP:** What evaluation would be needed?

### T. Difficult examiner questions

**T1. QUESTION:** Why trust any output if data is synthetic?  
**IDEAL ANSWER:** Trust it as a reproducible demonstration of code behavior, not as a real-world admission estimate.  
**KEY POINTS:** Scope of evidence.  
**LIKELY FOLLOW-UP:** What does it validate?

**T2. QUESTION:** Is 91.62% accuracy a success?  
**IDEAL ANSWER:** No; the forest predicts no positives and has zero recall.  
**KEY POINTS:** Majority class.  
**LIKELY FOLLOW-UP:** What is the baseline accuracy for always negative?

**T3. QUESTION:** Your docs say six training years. Is that accurate?  
**IDEAL ANSWER:** No; code fits on first four, holds out two, but `training_years` reports six total points.  
**KEY POINTS:** Own the discrepancy.  
**LIKELY FOLLOW-UP:** How would you correct it?

**T4. QUESTION:** Does SQLite let the user create accounts?  
**IDEAL ANSWER:** No; it persists a seeded demo user and session hashes but has no registration endpoint/UI.  
**KEY POINTS:** DB capability vs product flow.  
**LIKELY FOLLOW-UP:** What is stored in each table?

**T5. QUESTION:** What claim would you refuse to make?  
**IDEAL ANSWER:** That a campaign caused admissions, that a classifier is ready for real decisions, or that the forecast guarantees future enrollment.  
**KEY POINTS:** Evidence boundary.  
**LIKELY FOLLOW-UP:** What can you claim confidently?

## 20 must-remember questions

1. What is AdmitFlow? A local synthetic-data admission analytics prototype.
2. Exact title? “Admission Conversion Forecasting with Funnel Attribution and Scenario Simulation.”
3. Dataset size? 4,200 × 22.
4. Dataset source? Reproducible generator, seed 42; not real institutional data.
5. Target? `enrolled`, 351/4,200 = 8.36% positives.
6. Funnel volumes? 4,200 → 3,106 → 1,983 → 1,015 → 708 → 351.
7. Largest loss? Application-start to submitted, 1,123.
8. Does attribution show causality? No.
9. Classifiers? Logistic regression and 200-tree random forest.
10. Forest accuracy interpretation? 91.62% but zero positive predictions/recall.
11. ROC-AUC? 0.5573 logistic, 0.5195 forest; near chance.
12. Forecast model? LinearRegression on annual enrolment and index.
13. Forecast fit/holdout? First four years fit; last two held out; response field mislabels six total as training years.
14. Forecast errors? MAE 14.55, RMSE 15.5726, MAPE 27.33% on two points.
15. H1/H2/H4/H6? 74.2 / 77.3 / 83.5 / 89.7 for 2027/28/30/32.
16. Scenario type? Deterministic arithmetic, not ML or causal forecast.
17. Expected scenario? 5,000 apps → 2,479 submitted → 910 admitted → 435 enrolled.
18. AI architecture? Aggregate prompt context to Groq; not RAG and not sklearn.
19. Auth database? SQLite users/sessions; salted PBKDF2 password hash; SHA-256 session hash; seeded demo only.
20. Main limitation? Synthetic data, weak ML and short forecast; not production-ready.

## Glossary

| Term | One-line meaning | AdmitFlow use |
|---|---|---|
| Aggregate | Summary over multiple rows | Dashboard and LLM context values. |
| Applicant | One generated CSV row | Base unit counted by the app. |
| Attribution | Assign outcomes to recorded sources | Descriptive grouping by `campaign_source`. |
| Audit log | Record of actions | Last ten in-memory API events. |
| Average precision | Precision averaged over recall increases | Value returned as `pr_auc`. |
| Bearer token | Secret credential sent in Authorization header | Authenticates protected API calls. |
| Binary classification | Predict one of two labels | `enrolled` 0/1 classifier task. |
| Calibration | Agreement between predicted probabilities and frequencies | Not implemented/evaluated. |
| Categorical feature | Non-numeric group label | Programme, region, source, selectivity. |
| Causal inference | Estimate intervention effect against counterfactual | Not implemented; attribution is explicitly non-causal. |
| Cohort | Records grouped by shared dimension | Cycle, programme, region, source, selectivity groups. |
| Confusion matrix | Counts of correct/incorrect classes | Saved for both classifiers. |
| Conversion | Outcome proportion under a stated denominator | Funnel transition and group outcome rates. |
| Cross-validation | Repeated data splits for performance estimation | Not used. |
| CSV | Comma-separated tabular text | Analytics source data. |
| Data leakage | Information unavailable at prediction time enters training | Direct stage/outcome fields excluded; complete audit absent. |
| Deterministic | Same input produces same calculated output | Scenario engine. |
| Feature | Input variable used by a model | Twelve classifier inputs. |
| Feature importance | Estimator-relative signal score | Top ten forest impurity / absolute logistic coefficient. |
| Foreign key | Constraint linking records across tables | Session email references users email. |
| F1 | Harmonic mean of precision and recall | Threshold metric for classifiers. |
| Funnel | Ordered process stages and their counts | Lead through enrolment. |
| Generalization | Performance on unseen deployment-like cases | Not demonstrated on real data. |
| Holdout | Data reserved for evaluation | Classifier 25% random subset; forecast last two years. |
| Imbalanced target | Class frequencies differ substantially | Only 8.36% enrolled in current dataset. |
| Imputation | Fill missing feature values | Numeric median/categorical mode inside pipelines. |
| Linear regression | Fit a straight-line relation to numeric target | Annual enrolment forecast. |
| Log loss | Penalized error of probability predictions | Classifier metric returned by sklearn. |
| LocalStorage | Browser key/value persistence | Stores UI theme/sidebar and auth bearer token/user. |
| MAE | Mean absolute prediction error | Forecast error in enrolment counts. |
| MAPE | Mean absolute percentage error | Forecast metric, fraction displayed as percentage. |
| Migration | Versioned database schema change | No migration framework is present. |
| One-hot encoding | Binary indicator columns for categories | Model preprocessing. |
| PBKDF2 | Iterative password-based key derivation | Password hash storage. |
| Precision | Positive prediction correctness | Weak for logistic; zero forest. |
| PR-AUC | Precision/recall ranking summary | Implemented via sklearn average precision. |
| RAG | Retrieval-augmented generation | Not implemented; assistant gets prompt-time aggregates. |
| Recall | Fraction of actual positives detected | Zero for forest. |
| RMSE | Root mean squared prediction error | Forecast error with larger-error penalty. |
| ROC-AUC | Ranking quality over true/false-positive thresholds | Near-chance classifier scores. |
| Scenario | Output under explicit assumptions | Scaled deterministic funnel. |
| Session | Authenticated period represented by token | SQLite token hash and expiry. |
| Synthetic data | Artificial records produced by a generator | Entire applicant CSV. |
| Threshold | Probability cutoff for converting score to class | sklearn default prediction behavior; not tuned. |
| Train/test split | Divide data for fitting and evaluation | Stratified random 75/25 for classifiers. |
| Validation | Checks on data or model performance | Dataset checks and holdout metrics; not full correctness proof. |
| XSS | Script injection into a browser context | LocalStorage bearer token makes this a relevant risk; no CSP found. |

## Last 30 minutes before viva

- **Project:** AdmitFlow; exact topic is “Admission Conversion Forecasting with Funnel Attribution and Scenario Simulation.”
- **Data:** 4,200 synthetic rows, 22 columns, seed 42, cycles 2021–2026; no real institution source verified.
- **Stack:** Python 3.10.11, FastAPI, pandas, NumPy, scikit-learn; React 19/Vite 8, Recharts; SQLite only for auth.
- **Architecture:** React fetches JSON from FastAPI; backend reads CSV; analytics/model/forecast/scenario in separate modules; optional Groq assistant; local SQLite users/sessions; audit in memory.
- **Funnel:** 4,200 → 3,106 → 1,983 → 1,015 → 708 → 351; overall 8.36%; largest loss 1,123 app-start to submission.
- **Models:** Logistic regression and random forest; target `enrolled`; forest 91.62% accuracy but zero recall; AUCs 0.5573/0.5195. Neither is ready for decisions.
- **Forecast:** LinearRegression; first four cycles fit, last two holdout; H1/H2/H4/H6 = 74.2/77.3/83.5/89.7; MAPE 27.33%; six observations only; fit-year response bug.
- **Scenario:** Formula-driven, deterministic; expected 5,000 -> 2,479 -> 910 -> 435; no causal claim; campaign_shift does not affect counts.
- **Attribution:** Partner has most applications (749); Social has highest observed enrolment rate (9.64%); no causal inference.
- **AI:** Groq SDK/default `openai/gpt-oss-120b`; aggregate context only; JSON/Pydantic; not RAG; no streaming; key backend only.
- **Auth:** SQLite `users` + `sessions`; PBKDF2 310,000 iterations with 16-byte salt; SHA-256 token digest; eight-hour session; demo account only; no signup.
- **Audit:** In-memory, last ten; lost on restart.
- **Formulas:** Funnel stage conversion = next/current; overall = enrolled/all records; scenario = scale × multiplier then clamp; MAE/RMSE/MAPE as listed.
- **Limitations:** Synthetic-only data, weak classification, very short forecast, no causal attribution, scenario assumptions, local/demo security and non-durable audit.
- **Future:** Governed data; temporal/external model validation; corrected/refit forecast and uncertainty; account lifecycle; durable audit; production deployment.

## VIVA ACCURACY CHECK

### Verified from code

- Official academic title and scope wording in `docs/PROJECT_SPEC.md`.
- Dataset generator, seed, row/column count, actual dtypes, category domains, frequencies, flags, dates, missingness and duplicate-ID count.
- Validation checks and the no-op stage-rank block in `backend/admitflow/data_generator.py`.
- Funnel, dashboard, cohort, programme, region/selectivity and attribution formulas in `backend/admitflow/analytics.py`.
- Classifier features, preprocessing, split, estimator parameters, metrics, artifacts and report values in `backend/admitflow/ml.py` and `evidence/models/model_report.json`.
- Forecast split/model/horizons/metrics in `backend/admitflow/forecast.py` and `evidence/metrics/forecast_report.json`, including the mismatch between actual fit size and reported `training_years`.
- Scenario arithmetic and the unused-for-counts `campaign_shift` in `backend/admitflow/scenario.py` and `evidence/metrics/scenario_report.json`.
- Groq provider, model default, environment variables, prompt/context construction, JSON response validation and failures in `backend/admitflow/assistant.py` and `server.py`.
- All route declarations, request schemas, auth dependency, CORS and audit behavior in `backend/admitflow/server.py`.
- SQLite schema, PBKDF2 parameters, token-hash persistence, eight-hour expiry, seeded user and lack of account-creation route in `backend/admitflow/auth.py` and `config.py`.
- Frontend pages, state, requests, charts, interactions, theme, command search, loading/error handling and responsive breakpoints in `frontend/src/`.
- Dependency versions from current environment/lockfiles; test/evidence counts and build warning from available files/current run.
- A live authenticated assistant request returned HTTP 200 in this workspace on 2026-10-03; that one-off check is not in the older saved evidence manifest.

### Could not be verified

- Any real-world source, institution, applicant consent, representativeness, or deployment outcome for the synthetic CSV.
- Statistical significance or causal effect for programme, cohort, region or campaign differences.
- Whether a model will generalize to real applicants, or whether a campaign/scenario will change actual enrolments.
- Business costs, intervention budgets, admissions policies, real intended user counts, or institutional data governance beyond repository statements.
- Production availability/latency/security of Groq, or provider response quality across a representative question evaluation set.
- Exact SQLite library runtime version from the captured artifacts.
- A screenshot automation process inside `capture_evidence.py`; screenshots are listed but this script does not create them.

### Potential inconsistencies and discrepancies

1. `README.md` and older API/final verification prose describe JWT signing and `ADMITFLOW_JWT_SECRET`; current `auth.py` uses opaque random bearer tokens stored by hash in SQLite. `PyJWT` remains a declared/installed dependency but current authentication does not import it.
2. `docs/FINAL_VERIFICATION.md` and `docs/TESTING.md` report 20 backend tests; saved log confirms 20. Current source includes new SQLite persistence tests and a fresh run during this manual preparation passed 21; that newer output was not saved to the old log.
3. Forecast response/UI calls `training_years` six, but `evaluate_forecast()` fits on four rows (2021–2024), holds out two (2025–2026), and reuses the four-row fitted estimator for the future forecast.
4. Acceptance/project/architecture prose says leakage checks, temporal forecasting governance, calibration, or explainability more strongly than current implementation supports. Current classifier split is stratified random; no calibration, formal leakage test or threshold selection is coded.
5. Architecture blueprint suggests SQLAlchemy, visualization libraries and possible Gradient Boosting; actual app uses built-in sqlite3 for auth, Recharts in frontend, sklearn logistic regression/random forest/linear regression; no SQLAlchemy, matplotlib/seaborn/Plotly or Gradient Boosting was found.
6. Project docs say auth is JWT in some locations, whereas API docs were updated for SQLite-backed sessions. Current code has no registration UI/API; SQLite only stores the seeded demo account and sessions.
7. `campaign_shift` is accepted/defaulted/returned by the scenario engine but does not change scenario counts; frontend has no campaign-shift editor.
8. Architecture/documentation refers to `training_years` as observed years in places; this is total series length, not actual model fit count.
9. Evidence/final docs say a live Groq answer was not verified/no configured key, but an authenticated live call succeeded during current workspace work on 2026-10-03. Treat saved verification text as historical and provider status as environment-dependent.
10. Project-management tracker marks all 17 tasks completed; this is a workflow artifact and does not override the model/data/security limitations above.
