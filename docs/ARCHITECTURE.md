# Architecture Blueprint

## 1. High-level design

AdmitFlow follows a simple layered architecture designed for maintainability and academic clarity:

- data generation and validation layer
- analytical processing layer
- model and forecasting layer
- backend API layer
- frontend application layer
- evidence and tracking layer

## 2. System components

### Data layer

- reproducible synthetic admissions dataset generator
- schema and validation checks
- profile generation and data dictionary
- export to CSV/Parquet or repository datasets

### Analytics layer

- funnel analytics and stage conversion calculations
- cohort comparison logic
- programme comparison and selectivity analysis
- attribution calculations with descriptive framing
- forecasting and scenario utilities

### ML layer

- preprocessing pipeline for numerical and categorical features
- train/test split with leakage prevention
- baseline logistic regression model
- advanced tree-based model such as Random Forest or Gradient Boosting
- evaluation metrics and explainability outputs

### Backend layer

- FastAPI application
- SQLite-backed bearer sessions protecting analytics endpoints
- optional server-side Groq assistant grounded in aggregate analytics and scenario results
- process-local audit logging for user and scenario actions
- explicit Pydantic schemas for request and response models

### Frontend layer

- React single-page application
- dashboard and analytics pages
- filters, charts, and theme switcher
- error, loading, and empty states
- authentication and protected route flow

### Governance layer

- project tracker
- evidence register
- test register
- Git workflow and verification process

## 3. Recommended stack

- Python 3.10+
- FastAPI
- SQLAlchemy or lightweight data layer depending on persistence needs
- scikit-learn
- pandas, numpy
- matplotlib/seaborn or plotly for reporting
- React + Vite
- TypeScript or JavaScript
- openpyxl for tracker generation
- pytest for backend and validation tests

## 4. Design principles

- keep components small and explicit
- prefer direct code over abstraction-heavy patterns
- separate data generation, analytics, model, API, and UI responsibilities
- avoid hidden state and accidental leakage
- record evidence for each verified milestone

## 5. Verification architecture

The project uses a traceable evidence chain:

1. task defined in tracker
2. implementation executed
3. tests or evidence generation performed
4. output stored under `evidence/`
5. tracker status updated with file paths and verification notes
6. final docs confirm completion status

## 6. Risk controls

- avoid unsupported causal claims in attribution outputs
- keep dataset generation deterministic using a fixed seed
- verify train/test split boundaries and temporal checks for forecasting
- never expose secrets in frontend code or logs
- treat any unverified finding as `NOT VERIFIED`
