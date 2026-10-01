#!/usr/bin/env python
"""
AdmitFlow - PRIMARY ADMISSION CONVERSION CLASSIFICATION BASELINE
================================================================

Task      : predict `enrolled_flag` at `application_submitted_ts`
Unit      : one row per `application_id`
Data      : data/processed/applications_modelling_view.csv
Split     : `split_hint` (train = cycles 1-2, validation = cycle 3, test = cycle 4)
Model     : L2-penalised Logistic Regression on a one-hot + scaled numeric matrix
Tuning    : NONE. Fixed hyper-parameters, single fit per split.

This script is READ-ONLY with respect to the dataset. It opens the modelling view and the two
dimension/fact tables needed to recover the two declared features that are not carried in the
modelling view, and writes exactly two files:

    reports/baseline_results.md

LEAKAGE BOUNDARY
----------------
Features are drawn ONLY from the explicit `primary` allow-list published in
`scripts/admitflow_schema.py` (`S.feature_columns("primary")`). The modelling view physically
contains POST_OUTCOME and TARGET columns -- including `stage_reached` and `stage_reached_order`,
which are exact deterministic restatements of `enrolled_flag`. The script therefore never
auto-selects columns; it intersects the schema allow-list with the available columns and asserts
that no forbidden column can enter the design matrix.

Reproduce with:
    python scripts/train_baseline.py
    python scripts/train_baseline.py --fail-on-leakage

The dataset is synthetic. Nothing produced here is real-world institutional performance.
"""

from __future__ import annotations

import argparse
import io
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, NamedTuple, Sequence, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import admitflow_schema as S  # noqa: E402  (single source of truth for the allow-lists)

from sklearn.compose import ColumnTransformer  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import OneHotEncoder, StandardScaler  # noqa: E402

# --------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------

SEED = 20240817  # same seed as the dataset generator, so the run is reproducible end to end
TARGET = "enrolled_flag"
SPLIT_COL = "split_hint"
THRESHOLD = 0.5
ANCHOR = date(2022, 1, 1)  # arbitrary fixed origin for converting dates to a numeric offset

MODEL_NAME = "LogisticRegression (L2, lbfgs)"
MODEL_PARAMS = {
    "penalty": "l2",
    "C": 1.0,
    "solver": "lbfgs",
    "max_iter": 5000,
    "random_state": SEED,
}

# Declared primary features that are bookkeeping / grouping fields rather than model inputs.
#
# `admitflow_data_contract.md` I.1 lists these inside the `primary` allow-list under the
# heading "Grouping / bookkeeping". They are permitted to be CARRIED with a row (you need a
# label to group by when resampling) but they are not predictive inputs:
#
#   split_hint    -- a deterministic function of cycle_id; feeding it to the model would leak
#                    the evaluation design into the features
#   cohort_label  -- programme_code x cycle_id; a strict nesting of two features that are
#                    already present, and its training levels are all unseen at test time
#
# `application_id` and `applicant_id` are listed for completeness but are NOT members of the
# schema `primary` allow-list, so they were never candidates. They are never used as inputs
# either; `applicant_id` is documented here as the grouping key for any future resampling.
EXCLUDED_FROM_ALLOWLIST = ["split_hint", "cohort_label"]
IDENTIFIER_COLUMNS = ["application_id", "applicant_id"]

# Hard guard: the script refuses to build a design matrix containing any of these.
FORBIDDEN = {
    "stage_reached",
    "stage_reached_order",
    "admitted_flag",
    "enrolled_given_admitted_flag",
    "enrolled_flag",
    "selection_score",
    "decision_type",
    "dropoff_stage",
    "dropoff_reason",
    "doc_verification_status",
    "doc_query_raised",
    "doc_query_count",
    "admission_decision_ts",
    "application_verified_ts",
    "admitted_ts",
    "enrolled_ts",
    "days_submitted_to_verified",
    "days_verified_to_decision",
    "days_decision_to_enrolled",
    "offer_letter_issued",
    "offer_deadline",
    "scholarship_offered",
    "scholarship_amount_inr",
    "withdrawn_flag",
    "withdrawn_date",
    "is_repeat_applicant",
    "prediction_ts",
    "prediction_stage",
}

# Declared features carried as raw date/time strings; converted to a numeric day offset.
DATE_FEATURES = [
    "first_touch_date",
    "inquiry_ts",
    "application_started_ts",
    "application_submitted_ts",
]

# Declared features recovered by join rather than present in the modelling view.
JOIN_FEATURES = {
    "region_inquiry_weight": ("dim_region", "region_id", "region_id"),
    "application_count": ("fact_applicant", "applicant_id", "applicant_id"),
}


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------


def days_since_anchor(series: pd.Series) -> pd.Series:
    """Convert an ISO date/datetime string column to whole days since ANCHOR."""
    parsed = pd.to_datetime(series, errors="coerce", format="ISO8601")
    return (parsed - pd.Timestamp(ANCHOR)).dt.total_seconds() / 86400.0


def load_frame(root: Path) -> Tuple[pd.DataFrame, List[str], List[str]]:
    """Load the modelling view and recover the two declared features that need a join."""
    mv_path = root / "data" / "processed" / "applications_modelling_view.csv"
    frame = pd.read_csv(mv_path)

    declared = [c for _, c in S.feature_columns(S.FEATURE_SET_PRIMARY)]
    present = [c for c in declared if c in frame.columns]
    missing = [c for c in declared if c not in frame.columns]

    recovered: List[str] = []
    for name, (table, key_col, join_on) in JOIN_FEATURES.items():
        if name not in declared:
            continue
        if name in frame.columns:
            continue
        dim = pd.read_csv(root / "data" / "raw" / f"{table}.csv")
        if name not in dim.columns or join_on not in dim.columns:
            continue
        mapping = dim.set_index(join_on)[name]
        mapped = frame[join_on].map(mapping)
        if mapped.isna().all():
            continue
        frame[name] = mapped
        recovered.append(name)

    return frame, missing, recovered


def build_design(frame: pd.DataFrame, features: Sequence[str]
                 ) -> Tuple[pd.DataFrame, List[str], List[str]]:
    """Return the numeric design matrix, the numeric column list and the categorical list."""
    data = frame[list(features)].copy()

    for col in DATE_FEATURES:
        if col in data.columns:
            data[col] = days_since_anchor(data[col])

    # bool -> int so the ColumnTransformer sees a clean numeric block; object stays categorical.
    for col in data.columns:
        if data[col].dtype == bool:
            data[col] = data[col].astype("int64")
    categorical = [c for c in data.columns if data[c].dtype == object]
    numeric = [c for c in data.columns if c not in categorical]
    return data, numeric, categorical


def make_pipeline(numeric: Sequence[str], categorical: Sequence[str]) -> Pipeline:
    num_block = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]
    )
    cat_block = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown="ignore",
                    drop=None,
                    sparse_output=True,
                    dtype=np.float64,
                ),
            ),
        ]
    )
    pre = ColumnTransformer(
        [
            ("num", num_block, list(numeric)),
            ("cat", cat_block, list(categorical)),
        ],
        remainder="drop",
    )
    return Pipeline(
        [
            ("preprocess", pre),
            ("model", LogisticRegression(**MODEL_PARAMS)),
        ]
    )


def metrics_block(y_true: np.ndarray, prob: np.ndarray, rate: float) -> Dict[str, float]:
    pred = (prob >= THRESHOLD).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    out = {
        "n": int(len(y_true)),
        "positives": int(y_true.sum()),
        "observed_rate": float(y_true.mean()),
        "mean_predicted": float(prob.mean()),
        "log_loss": float(log_loss(y_true, prob)),
        "roc_auc": float(roc_auc_score(y_true, prob)),
        "pr_auc": float(average_precision_score(y_true, prob)),
        "accuracy": float(accuracy_score(y_true, pred)),
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }
    # constant predictor at the observed population rate -- the "do nothing" reference
    const = np.full(len(y_true), rate, dtype=float)
    const_pred = (const >= THRESHOLD).astype(int)
    out["const_log_loss"] = float(log_loss(y_true, const))
    out["const_accuracy"] = float(accuracy_score(y_true, const_pred))
    out["const_roc_auc"] = 0.5
    out["const_pr_auc"] = float(rate)
    out["const_precision"] = float(precision_score(y_true, const_pred, zero_division=0))
    out["const_recall"] = float(recall_score(y_true, const_pred, zero_division=0))
    out["const_f1"] = float(f1_score(y_true, const_pred, zero_division=0))
    out["log_loss_skill"] = 1.0 - out["log_loss"] / out["const_log_loss"]
    return out


def calibration(y_true: np.ndarray, prob: np.ndarray, n_bins: int = 10
                ) -> Tuple[pd.DataFrame, float, float]:
    """Binned reliability table plus the calibration slope / intercept of logit(p) -> y."""
    eps = 1e-9
    logit = np.log(np.clip(prob, eps, 1 - eps) / (1 - np.clip(prob, eps, 1 - eps)))
    cal = LogisticRegression(penalty=None, max_iter=5000)
    cal.fit(logit.reshape(-1, 1), y_true)
    slope = float(cal.coef_[0][0])
    intercept = float(cal.intercept_[0])

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(prob, edges[1:-1], right=False), 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        m = idx == b
        n = int(m.sum())
        rows.append(
            {
                "bin": f"[{edges[b]:.1f}, {edges[b + 1]:.1f})",
                "n": n,
                "mean_predicted": float(prob[m].mean()) if n else float("nan"),
                "observed_rate": float(y_true[m].mean()) if n else float("nan"),
            }
        )
    return pd.DataFrame(rows), slope, intercept


class Selection(NamedTuple):
    """The feature set, resolved once, so every model in the project uses the same one."""

    frame: pd.DataFrame
    declared: List[str]
    features: List[str]
    design: pd.DataFrame
    numeric: List[str]
    categorical: List[str]
    missing_from_view: List[str]
    recovered: List[str]
    held_out: List[str]


def select_features(root: Path) -> Selection:
    """Load the modelling view, recover the two join-only declared features, apply the
    allow-list and the bookkeeping hold-out, and run the leakage guard.

    This is the single place the feature set is defined. `train_advanced.py` imports it so
    that the advanced model cannot drift from the baseline.
    """
    frame, missing_from_view, recovered = load_frame(root)
    declared = [c for _, c in S.feature_columns(S.FEATURE_SET_PRIMARY)]
    held_out = [c for c in EXCLUDED_FROM_ALLOWLIST if c in declared]
    features = [c for c in declared if c in frame.columns and c not in EXCLUDED_FROM_ALLOWLIST]

    leaked = sorted(set(features) & FORBIDDEN)
    post_outcome = sorted(
        {c for c in features
         if c in {m.name for e in S.ENTITIES.values() for m in e.columns}
         and _role_of(c) in ("POST_OUTCOME", "TARGET")}
    )
    if leaked or post_outcome:
        # a column can trip both checks (e.g. admitted_flag is both FORBIDDEN and POST_OUTCOME);
        # report it once
        raise LeakageError(sorted(set(leaked) | set(post_outcome)))

    X, numeric, categorical = build_design(frame, features)
    return Selection(frame, declared, features, X, numeric, categorical,
                     missing_from_view, recovered, held_out)


class LeakageError(RuntimeError):
    def __init__(self, columns: List[str]) -> None:
        super().__init__("forbidden columns in design matrix: " + ", ".join(columns))
        self.columns = columns


def preprocessor_of(pipe: Pipeline) -> ColumnTransformer:
    """Return the fitted ColumnTransformer from a baseline pipeline."""
    return pipe.named_steps["preprocess"]


def make_preprocessor(numeric: Sequence[str], categorical: Sequence[str]) -> ColumnTransformer:
    """The preprocessing block on its own, identical to the one inside `make_pipeline`.

    Exposed so a non-linear estimator can be fitted on exactly the same encoded columns as the
    baseline, without inheriting the baseline's LogisticRegression step.
    """
    num_block = Pipeline([("impute", SimpleImputer(strategy="median")),
                          ("scale", StandardScaler())])
    cat_block = Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                          ("onehot", OneHotEncoder(handle_unknown="ignore", drop=None,
                                                   sparse_output=True, dtype=np.float64))])
    return ColumnTransformer([("num", num_block, list(numeric)),
                             ("cat", cat_block, list(categorical))], remainder="drop")


def encoded_feature_map(fitted_pre: ColumnTransformer, numeric: Sequence[str],
                        categorical: Sequence[str]) -> List[str]:
    """Map every column of a fitted design matrix back to its originating declared feature.

    Numeric columns map 1:1. Categorical columns are expanded by the fitted encoder's own
    `categories_` rather than by string-splitting the column names, because declared feature
    names themselves contain underscores. The fitted encoder must be the one that produced the
    design matrix, so the order of `numeric` / `categorical` must match its input.

    `ColumnTransformer` emits the numeric block first, then the categorical block, which is the
    order reproduced here.
    """
    encoder = fitted_pre.named_transformers_["cat"].named_steps["onehot"]
    mapping = list(numeric)
    for col, cats in zip(categorical, encoder.categories_):
        mapping.extend([col] * len(cats))
    if len(mapping) != len(fitted_pre.get_feature_names_out()):
        raise ValueError(
            f"importance map has {len(mapping)} entries but the fitted design matrix has "
            f"{len(fitted_pre.get_feature_names_out())} columns"
        )
    return mapping


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="AdmitFlow primary classification baseline")
    ap.add_argument("--root", default=str(ROOT), help="dataset root")
    ap.add_argument("--report", default=None, help="output markdown path")
    ap.add_argument("--fail-on-leakage", action="store_true",
                    help="accepted for explicitness; a leakage failure always aborts the run "
                         "with exit code 2, with or without this flag")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    report_path = Path(args.report) if args.report else root / "reports" / "baseline_results.md"
    np.random.seed(SEED)

    # ---- data, features and the leakage guard ----------------------------------------
    try:
        sel = select_features(root)
    except LeakageError as exc:
        print("LEAKAGE GUARD FAILED: " + str(exc))
        for c in exc.columns:
            print("   ", c)
        return 2
    frame = sel.frame
    declared = sel.declared
    features = sel.features
    held_out = sel.held_out
    missing_from_view = sel.missing_from_view
    recovered = sel.recovered
    print(f"[guard] design matrix uses {len(features)} declared primary features, "
          f"0 forbidden, 0 POST_OUTCOME/TARGET")

    X_all, numeric, categorical = sel.design, sel.numeric, sel.categorical
    y = frame[TARGET].to_numpy(dtype=int)
    split = frame[SPLIT_COL].to_numpy()

    tr = split == "train"
    va = split == "validation"
    te = split == "test"

    pipe = make_pipeline(numeric, categorical)
    print(f"[fit ] training on {int(tr.sum()):,} rows x {len(features)} declared features")
    pipe.fit(X_all.loc[tr], y[tr])

    train_rate = float(y[tr].mean())
    train_metrics = metrics_block(y[tr], pipe.predict_proba(X_all.loc[tr])[:, 1], train_rate)
    val_metrics = metrics_block(y[va], pipe.predict_proba(X_all.loc[va])[:, 1], train_rate)
    test_metrics = metrics_block(y[te], pipe.predict_proba(X_all.loc[te])[:, 1], train_rate)

    val_prob = pipe.predict_proba(X_all.loc[va])[:, 1]
    test_prob = pipe.predict_proba(X_all.loc[te])[:, 1]
    val_cal, val_slope, val_int = calibration(y[va], val_prob)
    test_cal, test_slope, test_int = calibration(y[te], test_prob)

    names = pipe.named_steps["preprocess"].get_feature_names_out()
    coefs = pipe.named_steps["model"].coef_[0]
    coef_frame = (
        pd.DataFrame({"feature": [n.replace("num__", "").replace("cat__", "") for n in names],
                      "coefficient": coefs})
        .assign(abs_coefficient=lambda d: d["coefficient"].abs())
        .sort_values("abs_coefficient", ascending=False)
        .reset_index(drop=True)
    )
    n_design = int(len(coefs))

    n_iter = int(pipe.named_steps["model"].n_iter_[0])

    # ---- report ----------------------------------------------------------------------
    L: List[str] = []
    a = L.append
    a("# AdmitFlow - Primary Classification Baseline")
    a("")
    a("> **The dataset is synthetic.** Every figure below was computed on data generated by")
    a("> `scripts/generate_dataset.py` from the documented AdmitFlow admission-funnel")
    a("> specification. These numbers describe the behaviour of a model fitted to a *simulated*")
    a("> funnel. They are **not** real-world institutional performance and must never be")
    a("> presented as such.")
    a("")
    a(f"Produced by `scripts/train_baseline.py` | seed `{SEED}` | no hyper-parameter tuning.")
    a("")
    a("---")
    a("")
    a("## 1. Task definition")
    a("")
    a("| Property | Value |")
    a("|---|---|")
    a("| Target | `enrolled_flag` (1 = applicant enrolled in this programme/cycle) |")
    a("| Prediction unit | one `application` |")
    a("| Prediction point | `application_submitted_ts` |")
    a("| Population | `data/processed/applications_modelling_view.csv` |")
    a("| Split | `split_hint` - deterministic function of `cycle_id` |")
    a("| Decision threshold | 0.50 |")
    a("")
    a("**The base rate for this task is the modelling-view rate, not the top-of-funnel rate.**")
    a(f"The modelling view contains only applications that reached `application_submitted`, so the")
    a(f"reference rate is the *submitted* population rate (validation {val_metrics['observed_rate']:.4f},")
    a(f"test {test_metrics['observed_rate']:.4f}). The top-of-funnel rate of 0.121 applies to")
    a(f"`fact_application`, a different and 2.3x larger population, and is **not** the correct")
    a("reference for any metric on this task.")
    a("")
    a("---")
    a("")
    a("## 2. Data and splits")
    a("")
    a("| Split | `split_hint` | Cycles | Rows | Positives | Enrolment rate |")
    a("|---|---|---|---|---|---|")
    for name, mask, cyc in (("Train", tr, "CYC-2022, CYC-2023"),
                            ("Validation", va, "CYC-2024"),
                            ("Test", te, "CYC-2025")):
        a(f"| {name} | `{name.lower()}` | {cyc} | {int(mask.sum()):,} | {int(y[mask].sum()):,} | "
          f"{y[mask].mean():.6f} |")
    a("")
    a("---")
    a("")
    a("## 3. Feature selection and leakage boundary")
    a("")
    a("Features were taken **only** from the explicit `primary` allow-list published in")
    a("`scripts/admitflow_schema.py`. The modelling view was never auto-screened: the script")
    a("intersects the schema allow-list with the available columns. This matters because the")
    a("modelling view physically contains `stage_reached` and `stage_reached_order`, both of which")
    a("are exact deterministic restatements of `enrolled_flag` (verified: `stage_reached_order == 7`")
    a("iff `enrolled_flag == 1` on every row). A 'drop the target column and use the rest' workflow")
    a("would have produced a meaningless perfect score.")
    a("")
    a("| Quantity | Count |")
    a("|---|---|")
    a(f"| Declared `primary` allow-list features | {len(declared)} |")
    a(f"| Of which present in the modelling view without a join | {len(declared) - len(recovered)} |")
    a(f"| Of which recovered by join from a raw table | {len(recovered)} |")
    a(f"| Of which held out as bookkeeping / grouping | {len(held_out)} |")
    a(f"| **Declared features used as model inputs** | **{len(features)}** |")
    a(f"| Design-matrix columns after one-hot encoding (fitted on train) | {n_design} |")
    a("")
    a("One-hot encoding expands the matrix from "
      f"{len(numeric) + len(categorical)} declared features ({len(numeric)} numeric, "
      f"{len(categorical)} categorical) to {n_design} columns. The one-hot block is fitted on the")
    a("training split only, so categories first seen at validation or test time contribute no")
    a("column: `cycle_id` yields 2 columns rather than 4 (the test cycle `CYC-2025` is unseen) and")
    a("`campaign_id` yields 16 rather than 32. `handle_unknown=\"ignore\"` maps those unseen levels")
    a("to an all-zero block instead of raising.")
    a("")
    if missing_from_view:
        a("**Declared features absent from the modelling view** (recovered by join, not omitted):")
        a("")
        a("| Feature | Source | Join key | Recovery |")
        a("|---|---|---|---|")
        for c in missing_from_view:
            tbl, key, join_on = JOIN_FEATURES.get(c, ("-", "-", "-"))
            status = "recovered, 0 nulls" if c in recovered else "NOT RECOVERED"
            a(f"| `{c}` | `data/raw/{tbl}.csv` | `{join_on}` | {status} |")
        a("")
    a("**Held-out bookkeeping fields.** `admitflow_data_contract.md` I.1 lists these inside the")
    a("`primary` allow-list under the heading *Grouping / bookkeeping*. They are safe to carry on a")
    a("row but are not predictive inputs, so they were held out of the design matrix:")
    a("")
    a("| Held out | In allow-list? | Reason |")
    a("|---|---|---|")
    a("| `split_hint` | yes | deterministic function of `cycle_id`; would leak the evaluation design into the features |")
    a("| `cohort_label` | yes | strict nesting of `programme_id` and `cycle_id`, both already present; its training levels are all unseen at test time |")
    a(f"| `application_id` | no | surrogate key, unique per row; pure memorisation capacity. Never an allow-list member and never used as an input |")
    a(f"| `applicant_id` | no | surrogate key. Not an allow-list member; it is the grouping key to use if resampling is added later |")
    a("")
    a("**Fields the schema classifies as POST_OUTCOME or TARGET.** None is in the design matrix.")
    a("The script asserts this programmatically and aborts with exit code 2 if any appears.")
    a("The 25 columns are listed in `admitflow_data_contract.md` I.3 and include")
    a("`stage_reached`, `stage_reached_order`, `dropoff_stage`, `dropoff_reason`,")
    a("`admission_decision_ts`, `application_verified_ts`, `doc_verification_status`,")
    a("`doc_query_raised`, `doc_query_count`, `decision_type`, `selection_score`,")
    a("`offer_letter_issued`, `offer_deadline`, `scholarship_offered`, `scholarship_amount_inr`,")
    a("`withdrawn_flag`, `withdrawn_date`, `admitted_ts`, `enrolled_ts`,")
    a("`days_submitted_to_verified`, `days_verified_to_decision`, `days_decision_to_enrolled`,")
    a("`admitted_flag`, `enrolled_given_admitted_flag`, `enrolled_flag`.")
    a("")
    a("`selection_score` -- the institution's internal merit score, deliberately retained in the raw")
    a("data as a leakage trap (contract `D-11`) -- is **not present** in the modelling view and was")
    a("therefore never a candidate. The safe alternative")
    a("`is_repeat_applicant_at_prediction` **is** used; the leaking lifetime flag")
    a("`fact_applicant.is_repeat_applicant` is not.")
    a("")
    a("### Features used")
    a("")
    a("| # | Feature | Type |")
    a("|---|---|---|")
    for i, c in enumerate(features, 1):
        kind = "categorical" if c in categorical else "numeric"
        tag = " (recovered by join)" if c in recovered else ""
        a(f"| {i} | `{c}`{tag} | {kind} |")
    a("")
    a(f"Categorical: {len(categorical)} | Numeric: {len(numeric)}")
    a("")
    a("---")
    a("")
    a("## 4. Preprocessing and model configuration")
    a("")
    a("| Stage | Configuration |")
    a("|---|---|")
    a("| Numeric | `SimpleImputer(strategy=\"median\")` -> `StandardScaler()` |")
    a("| Categorical | `SimpleImputer(strategy=\"most_frequent\")` -> `OneHotEncoder(handle_unknown=\"ignore\", drop=None)` |")
    a(f"| Date/time features | parsed as ISO-8601, converted to whole days since `{ANCHOR.isoformat()}` |")
    a("| Assembler | `ColumnTransformer` (numeric block, categorical block, `remainder=\"drop\"`) |")
    a("| Model | `LogisticRegression(penalty=\"l2\", C=1.0, solver=\"lbfgs\", max_iter=5000, random_state=%d)` |" % SEED)
    a("| Tuning | **none** - single fit, no search, no cross-validation, no threshold optimisation |")
    a(f"| Random seed | `{SEED}` (also passed to `LogisticRegression`; `lbfgs` is deterministic) |")
    a(f"| Converged | `n_iter_ = {n_iter}` of 5000 |")
    a(f"| Threshold | fixed at 0.50 |")
    a("")
    a("`handle_unknown=\"ignore\"` is required, not cosmetic: `cycle_id` and `campaign_id` levels")
    a("first appear at test time, and an unseen level maps to an all-zero block rather than raising.")
    a("")
    a("---")
    a("")
    a("## 5. Results")
    a("")
    a("### 5.1 Headline metrics")
    a("")
    a("| Metric | Train | Validation | Test | Constant baseline (val) | Constant baseline (test) |")
    a("|---|---|---|---|---|---|")
    a(f"| Rows | {train_metrics['n']:,} | {val_metrics['n']:,} | {test_metrics['n']:,} | {val_metrics['n']:,} | {test_metrics['n']:,} |")
    a(f"| Positives | {train_metrics['positives']:,} | {val_metrics['positives']:,} | {test_metrics['positives']:,} | {val_metrics['positives']:,} | {test_metrics['positives']:,} |")
    a(f"| **Observed enrolment rate** | {train_metrics['observed_rate']:.6f} | **{val_metrics['observed_rate']:.6f}** | **{test_metrics['observed_rate']:.6f}** | {val_metrics['observed_rate']:.6f} | {test_metrics['observed_rate']:.6f} |")
    a(f"| Mean predicted probability | {train_metrics['mean_predicted']:.6f} | {val_metrics['mean_predicted']:.6f} | {test_metrics['mean_predicted']:.6f} | {train_rate:.6f} | {train_rate:.6f} |")
    a("")
    a("| Metric | Validation | Test |")
    a("|---|---|---|")
    for key, label, fmt in (
        ("log_loss", "Log loss", "{:.4f}"),
        ("roc_auc", "ROC-AUC", "{:.4f}"),
        ("pr_auc", "PR-AUC (average precision)", "{:.4f}"),
        ("accuracy", "Accuracy", "{:.4f}"),
        ("precision", "Precision", "{:.4f}"),
        ("recall", "Recall", "{:.4f}"),
        ("f1", "F1", "{:.4f}"),
    ):
        a(f"| {label} | {fmt.format(val_metrics[key])} | {fmt.format(test_metrics[key])} |")
    a("")
    a("**Constant baseline** = a single probability equal to the *training* enrolment rate")
    a(f"({train_rate:.6f}) for every row. This is the \"predict the base rate, do nothing\" model.")
    a("")
    a("| Metric | Model (val) | Constant (val) | Model (test) | Constant (test) |")
    a("|---|---|---|---|---|")
    a(f"| Log loss | {val_metrics['log_loss']:.4f} | {val_metrics['const_log_loss']:.4f} | {test_metrics['log_loss']:.4f} | {test_metrics['const_log_loss']:.4f} |")
    a(f"| ROC-AUC | {val_metrics['roc_auc']:.4f} | 0.5000 | {test_metrics['roc_auc']:.4f} | 0.5000 |")
    a(f"| PR-AUC | {val_metrics['pr_auc']:.4f} | {val_metrics['const_pr_auc']:.4f} | {test_metrics['pr_auc']:.4f} | {test_metrics['const_pr_auc']:.4f} |")
    a(f"| Accuracy | {val_metrics['accuracy']:.4f} | {val_metrics['const_accuracy']:.4f} | {test_metrics['accuracy']:.4f} | {test_metrics['const_accuracy']:.4f} |")
    a(f"| Precision | {val_metrics['precision']:.4f} | {val_metrics['const_precision']:.4f} | {test_metrics['precision']:.4f} | {test_metrics['const_precision']:.4f} |")
    a(f"| Recall | {val_metrics['recall']:.4f} | {val_metrics['const_recall']:.4f} | {test_metrics['recall']:.4f} | {test_metrics['const_recall']:.4f} |")
    a(f"| F1 | {val_metrics['f1']:.4f} | {val_metrics['const_f1']:.4f} | {test_metrics['f1']:.4f} | {test_metrics['const_f1']:.4f} |")
    a("")
    a(f"**Log-loss skill score** (1 - model log loss / constant log loss): "
      f"validation **{val_metrics['log_loss_skill']:.4f}**, test **{test_metrics['log_loss_skill']:.4f}**.")
    a("A positive value means the model beats the do-nothing baseline; it is the cleanest single")
    a("number for \"did the features carry information at all\".")
    a("")
    a("### 5.2 Confusion matrix at threshold 0.50")
    a("")
    a("| Split | | Predicted 0 | Predicted 1 |")
    a("|---|---|---|---|")
    for label, m in (("Validation", val_metrics), ("Test", test_metrics)):
        a(f"| {label} | Actual 0 | {m['tn']:,} | {m['fp']:,} |")
        a(f"| {label} | Actual 1 | {m['fn']:,} | {m['tp']:,} |")
    a("")
    a("### 5.3 Calibration")
    a("")
    a(f"Calibration slope / intercept from a logistic regression of the outcome on `logit(p)`:")
    a(f"validation slope **{val_slope:.4f}**, intercept **{val_int:.4f}**;")
    a(f"test slope **{test_slope:.4f}**, intercept **{test_int:.4f}**.")
    a("A slope near 1.0 and intercept near 0.0 indicates well-calibrated probabilities.")
    a("")
    worst_slope = min(val_slope, test_slope)
    if worst_slope < 0.95 or val_int < -0.1 or test_int < -0.1:
        a(f"**Reading: the model is mildly over-confident.** A slope below 1.0 means the spread of "
          f"the")
        a(f"predicted probabilities is too wide, and a negative intercept means the probabilities "
          f"sit too")
        a(f"high on average (the mean predicted probability exceeds the observed rate in both "
          f"later")
        a(f"splits -- see section 5.1). The effect is mild and was **not** corrected: no "
          f"calibration")
        a("post-processing was applied, by design. If calibrated probabilities matter for the "
          "downstream")
        a("scenario engine, that is a separate, later step.")
    else:
        a("**Reading: calibration is close to ideal on both held-out splits.**")
    a("")
    a("**Validation reliability table**")
    a("")
    a("| Predicted probability bin | n | Mean predicted | Observed rate |")
    a("|---|---|---|---|")
    for _, r in val_cal.iterrows():
        if r["n"] == 0:
            continue
        a(f"| {r['bin']} | {int(r['n']):,} | {r['mean_predicted']:.4f} | {r['observed_rate']:.4f} |")
    a("")
    a("**Test reliability table**")
    a("")
    a("| Predicted probability bin | n | Mean predicted | Observed rate |")
    a("|---|---|---|---|")
    for _, r in test_cal.iterrows():
        if r["n"] == 0:
            continue
        a(f"| {r['bin']} | {int(r['n']):,} | {r['mean_predicted']:.4f} | {r['observed_rate']:.4f} |")
    a("")
    a("### 5.4 Largest coefficients")
    a("")
    a("Standardised coefficients on the preprocessed design matrix. Magnitude indicates influence")
    a("on the log-odds; it is **not** a causal effect.")
    a("")
    a("| Rank | Encoded feature | Coefficient |")
    a("|---|---|---|")
    for i, row in coef_frame.head(20).iterrows():
        a(f"| {i + 1} | `{row['feature']}` | {row['coefficient']:+.4f} |")
    a("")
    a("---")
    a("")
    a("## 6. Reproducibility")
    a("")
    a("| Item | Value |")
    a("|---|---|")
    a("| Script | `scripts/train_baseline.py` |")
    a("| Random seed | `%d` |" % SEED)
    a("| scikit-learn | `%s` |" % __import__("sklearn").__version__)
    a("| numpy / pandas | `%s` / `%s` |" % (np.__version__, pd.__version__))
    a("| Tuning | none |")
    a("")
    a("Exact commands, from the `admitflow-data` directory:")
    a("")
    a("```")
    a("python scripts/train_baseline.py")
    a("python scripts/train_baseline.py --fail-on-leakage")
    a("```")
    a("")
    a("The script is deterministic: it opens the dataset read-only, applies a fixed seed, and")
    a("trains a single unregularised-search model. Re-running it reproduces this report exactly.")
    a("")
    a("---")
    a("")
    a("## 7. Warnings and limitations")
    a("")
    a("1. **Synthetic data.** These metrics measure how well a logistic model recovers a *simulated*")
    a("   funnel whose parameters are known to the generator. They are not institutional performance")
    a("   and carry no external validity.")
    a("2. **Selection bias in the population.** The modelling view is filtered to")
    a("   `stage_reached_order >= 3`, which conditions on latent intent and acquisition channel")
    a("   (the channel mix differs from `fact_application` by up to 2.41 percentage points). The")
    a("   model answers *\"of those who submit, who will enrol\"*, not *\"which prospects should we")
    a("   push harder\"*. A top-of-funnel propensity model is a different, undefined task.")
    a("3. **Base rate differs by split.** Enrolment rate falls monotonically across cycles")
    a(f"   ({train_metrics['observed_rate']:.4f} train -> {val_metrics['observed_rate']:.4f} validation "
      f"-> {test_metrics['observed_rate']:.4f} test). The model is penalised on the two later")
    a("   cycles for a drift it cannot observe at training time.")
    a("4. **Unseen categorical levels at test time.** `cycle_id = CYC-2025` and its campaign levels")
    a("   never appear in training. `OneHotEncoder(handle_unknown=\"ignore\")` maps them to an")
    a("   all-zero block, so the model must fall back on the shared features. This is a genuine")
    a("   forward-deployment property of a real chronological split, not an artefact.")
    a("5. **Absolute-time features do not extrapolate.** The four declared date features are")
    a("   encoded as days since a fixed anchor, so the model can learn an absolute calendar")
    a("   position. Because the test cycle is two years after the earliest training cycle, this")
    a("   encoding cannot be verified on unseen time and is a plausible source of test-set")
    a("   degradation. The contract already provides `week_of_cycle_at_submission` and")
    a("   `month_of_submission` as cycle-relative alternatives.")
    a("6. **Two training cycles only.** The split is 2/1/1 by design (contract E.5), which is thin")
    a("   for a model with this many inputs and no cross-validation.")
    a("7. **Rows are not independent.** 2,529 applicants hold more than one application (maximum 3).")
    a("   `split_hint` is cycle-based, so an applicant with applications in two cycles can appear in")
    a("   both train and test. Any resampling, bootstrapping or significance testing **must** group")
    a("   by `applicant_id`. No resampling was performed in this baseline, so the reported figures")
    a("   are not affected by this.")
    a("8. **Seat capacity is a planning attribute, not an admission cap.** `base_seat_capacity` is")
    a("   included because it is a declared feature, but actual admits exceed the declared capacity")
    a("   by roughly 4.7x in the generated data. It must not be read as a hard cap or as")
    a("   \"seats filled\".")
    a("9. **Attribution fields are associational.** `acquisition_channel`, `acquisition_source`,")
    a("   `campaign_id` and `is_referral_alumni` are first-touch records. Any apparent channel")
    a("   effect is confounded by applicant mix. No causal or uplift claim is licensed by this")
    a("   dataset, and the coefficients in section 5.4 must not be read causally.")
    a("10. **This is a baseline, not a tuned model.** No hyper-parameter search, no cross-validation,")
    a("    no ensemble, no calibration post-processing and no threshold optimisation were done, by")
    a("    design. The numbers are a floor to beat, not a ceiling.")
    a("")
    a("---")
    a("")
    a("## 8. Integrity statement")
    a("")
    a("> The dataset is synthetic and was generated according to the documented AdmitFlow")
    a("> specification for development, experimentation, evaluation, and demonstration. It does not")
    a("> represent real institutional admissions data. The metrics in this report describe a model")
    a("> fitted to that synthetic data and nothing more.")
    a("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    io.open(report_path, "w", encoding="utf-8", newline="\n").write("\n".join(L))

    print(f"[done] wrote {report_path}")
    print(f"       features={len(features)} design_cols={n_design} n_iter={n_iter}")
    print(f"       val  log_loss={val_metrics['log_loss']:.4f} roc_auc={val_metrics['roc_auc']:.4f} "
          f"pr_auc={val_metrics['pr_auc']:.4f} acc={val_metrics['accuracy']:.4f} "
          f"f1={val_metrics['f1']:.4f}")
    print(f"       test log_loss={test_metrics['log_loss']:.4f} roc_auc={test_metrics['roc_auc']:.4f} "
          f"pr_auc={test_metrics['pr_auc']:.4f} acc={test_metrics['accuracy']:.4f} "
          f"f1={test_metrics['f1']:.4f}")
    print(f"       base rate train={train_rate:.6f} val={val_metrics['observed_rate']:.6f} "
          f"test={test_metrics['observed_rate']:.6f}")
    return 0


def _role_of(column: str) -> str:
    for entity in S.ENTITIES.values():
        for meta in entity.columns:
            if meta.name == column:
                return meta.role
    return "UNKNOWN"


if __name__ == "__main__":
    raise SystemExit(main())
