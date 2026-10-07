from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, log_loss, precision_score, recall_score, roc_auc_score, average_precision_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .config import MODEL_ARTIFACT_PATH


FEATURES = [
    "programme",
    "selectivity",
    "region",
    "campaign_source",
    "academic_score",
    "gpa",
    "engagement_score",
    "interest_score",
    "outreach_count",
    "campaign_clicks",
    "distance_km",
    "cycle_year",
]


def prepare_model_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    model_df = df[FEATURES + ["enrolled"]].copy()
    model_df["enrolled"] = model_df["enrolled"].astype(int)
    return model_df[FEATURES], model_df["enrolled"]


def train_model(df: pd.DataFrame, artifact_path: str | Path = MODEL_ARTIFACT_PATH) -> dict:
    X, y = prepare_model_data(df)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    numerical = [col for col in X.columns if pd.api.types.is_numeric_dtype(X[col].dtype)]
    categorical = [col for col in X.columns if col not in numerical]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), numerical),
            ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("encoder", OneHotEncoder(handle_unknown="ignore"))]), categorical),
        ]
    )

    baseline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)),
        ]
    )
    advanced = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", RandomForestClassifier(n_estimators=200, random_state=42, min_samples_leaf=2)),
        ]
    )

    baseline.fit(X_train, y_train)
    advanced.fit(X_train, y_train)

    artifact_path = Path(artifact_path)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"baseline": baseline, "advanced": advanced}, artifact_path)

    metrics = {
        "baseline": evaluate_model(baseline, X_test, y_test),
        "advanced": evaluate_model(advanced, X_test, y_test),
    }
    metrics["baseline"]["model"] = "Logistic Regression"
    metrics["advanced"]["model"] = "Random Forest"

    return metrics


def evaluate_model(model, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    estimator = model.named_steps["model"]
    feature_names = model.named_steps["preprocessor"].get_feature_names_out()
    if hasattr(estimator, "feature_importances_"):
        feature_scores = estimator.feature_importances_
        score_label = "importance"
    else:
        feature_scores = np.abs(estimator.coef_[0])
        score_label = "absolute_coefficient"
    top_features = [
        {"feature": str(feature_names[index]), score_label: round(float(feature_scores[index]), 6)}
        for index in np.argsort(feature_scores)[::-1][:10]
    ]

    return {
        "log_loss": round(float(log_loss(y_test, y_proba)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, y_proba)), 4),
        "pr_auc": round(float(average_precision_score(y_test, y_proba)), 4),
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "top_features": top_features,
    }


def save_model_report(metrics: dict, path: str | Path = "data/model_report.json") -> dict:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    import pandas as pd
    df = pd.read_csv("data/admission_data.csv")
    print(train_model(df))
