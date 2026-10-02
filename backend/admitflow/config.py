from pathlib import Path
import os
import secrets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
EVIDENCE_DIR = PROJECT_ROOT / "evidence"
BACKEND_DIR = PROJECT_ROOT / "backend"

DATASET_PATH = DATA_DIR / "admission_data.csv"
VALIDATION_REPORT_PATH = DATA_DIR / "validation_report.json"
MODEL_DIR = DATA_DIR / "models"
MODEL_ARTIFACT_PATH = MODEL_DIR / "admitflow_model.joblib"

JWT_SECRET = os.getenv("ADMITFLOW_JWT_SECRET") or secrets.token_urlsafe(48)
if len(JWT_SECRET) < 32:
	raise ValueError("ADMITFLOW_JWT_SECRET must contain at least 32 characters.")
DEMO_USER_EMAIL = "admin@admitflow.local"
DEMO_USER_PASSWORD = "admin123"
