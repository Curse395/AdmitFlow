from pathlib import Path
import os
import secrets
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")
DATA_DIR = PROJECT_ROOT / "data"
EVIDENCE_DIR = PROJECT_ROOT / "evidence"
BACKEND_DIR = PROJECT_ROOT / "backend"

DATASET_PATH = DATA_DIR / "admission_data.csv"
VALIDATION_REPORT_PATH = DATA_DIR / "validation_report.json"
MODEL_DIR = DATA_DIR / "models"
MODEL_ARTIFACT_PATH = MODEL_DIR / "admitflow_model.joblib"
AUTH_DB_PATH = DATA_DIR / "admitflow_auth.sqlite3"

DEMO_USER_EMAIL = "admin@admitflow.local"
DEMO_USER_PASSWORD = "admin123"
