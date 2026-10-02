from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from .analytics import attribution_summary, cohort_summary, cycle_comparison, dashboard_metrics, funnel_overview, programme_comparison, region_summary, selectivity_summary
from .auth import authenticate, oauth_configured, validate_token
from .config import DATASET_PATH
from .forecast import forecast_horizons
from .ml import save_model_report, train_model
from .scenario import scenario_engine

app = FastAPI(title="AdmitFlow API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

AUDIT_LOG: list[dict[str, Any]] = []
bearer_scheme = HTTPBearer(auto_error=False)


def load_dataset() -> pd.DataFrame:
    return pd.read_csv(DATASET_PATH)


class LoginRequest(BaseModel):
    email: str
    password: str


class ScenarioRequest(BaseModel):
    application_volume: int = Field(default=5000, ge=0)
    stage_adjustments: dict | None = None
    campaign_shift: dict | None = None


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    try:
        user = validate_token(credentials.credentials)
        return user
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "AdmitFlow API"}


@app.post("/auth/login")
def login(payload: LoginRequest) -> dict[str, Any]:
    try:
        token = authenticate(payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    AUDIT_LOG.append({"action": "login", "email": payload.email, "status": "success"})
    return {"token": token, "user": {"email": payload.email, "role": "admin"}}


@app.post("/auth/logout")
def logout(token: str) -> dict[str, Any]:
    try:
        validate_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    AUDIT_LOG.append({"action": "logout", "status": "success"})
    return {"status": "logged_out"}


@app.get("/auth/oauth")
def oauth_status() -> dict[str, Any]:
    return {
        "configured": oauth_configured(),
        "providers": ["Google", "GitHub"] if oauth_configured() else [],
        "note": "OAuth configuration is optional and requires external credentials. Local demo auth remains available without secrets.",
    }


@app.get("/api/dashboard", dependencies=[Depends(get_current_user)])
def dashboard() -> dict[str, Any]:
    df = load_dataset()
    metrics = dashboard_metrics(df)
    return metrics


@app.get("/api/funnel", dependencies=[Depends(get_current_user)])
def funnel() -> dict[str, Any]:
    df = load_dataset()
    return funnel_overview(df)


@app.get("/api/cohorts", dependencies=[Depends(get_current_user)])
def cohorts() -> dict[str, Any]:
    df = load_dataset()
    return {
        "cycle": cohort_summary(df, "cycle_year").to_dict(orient="records"),
        "programme": cohort_summary(df, "programme").to_dict(orient="records"),
        "region": region_summary(df).to_dict(orient="records"),
        "selectivity": selectivity_summary(df).to_dict(orient="records"),
    }


@app.get("/api/programmes", dependencies=[Depends(get_current_user)])
def programmes() -> list[dict[str, Any]]:
    df = load_dataset()
    return programme_comparison(df).to_dict(orient="records")


@app.get("/api/forecast", dependencies=[Depends(get_current_user)])
def forecast() -> dict[str, Any]:
    df = load_dataset()
    return forecast_horizons(df)


@app.get("/api/scenarios", dependencies=[Depends(get_current_user)])
def scenarios() -> dict[str, Any]:
    df = load_dataset()
    return scenario_engine(df)


@app.post("/api/scenarios/run", dependencies=[Depends(get_current_user)])
def run_scenario(payload: ScenarioRequest) -> dict[str, Any]:
    df = load_dataset()
    result = scenario_engine(df, payload.application_volume, payload.stage_adjustments, payload.campaign_shift)
    AUDIT_LOG.append({"action": "scenario_execution", "volume": payload.application_volume, "status": "success"})
    return result


@app.get("/api/model", dependencies=[Depends(get_current_user)])
def model_info() -> dict[str, Any]:
    df = load_dataset()
    metrics = train_model(df)
    save_model_report(metrics, "evidence/models/model_report.json")
    return metrics


@app.get("/api/audit", dependencies=[Depends(get_current_user)])
def audit() -> list[dict[str, Any]]:
    return list(AUDIT_LOG[-10:])


@app.get("/api/attribution", dependencies=[Depends(get_current_user)])
def attribution() -> list[dict[str, Any]]:
    df = load_dataset()
    return attribution_summary(df).to_dict(orient="records")


@app.get("/api/cycle", dependencies=[Depends(get_current_user)])
def cycle() -> list[dict[str, Any]]:
    df = load_dataset()
    return cycle_comparison(df).to_dict(orient="records")
