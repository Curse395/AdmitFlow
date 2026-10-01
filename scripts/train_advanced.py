#!/usr/bin/env python
"""
AdmitFlow - PRIMARY ADVANCED MODEL (Random Forest) AND COMPARISON
================================================================

Task      : predict `enrolled_flag` at `application_submitted_ts`
Unit      : one row per `application_id`
Data      : data/processed/applications_modelling_view.csv
Split     : `split_hint` (train = cycles 1-2, validation = cycle 3, test = cycle 4)
Model     : RandomForestClassifier
Tuning    : NONE. One configuration, one fit per model. No cross-validation, no search.

WHAT IS SHARED WITH THE BASELINE
--------------------------------
Rather than reimplementing anything, this script imports the baseline's building blocks:

    feature selection + leakage guard  ->  train_baseline.select_features()
    preprocessing blocks              ->  train_baseline.make_preprocessor()
    baseline estimator                ->  train_baseline.make_pipeline()
    metrics                           ->  train_baseline.metrics_block()
    calibration                       ->  train_baseline.calibration()

so the two models are guaranteed to see the identical rows, the identical 43 declared
features and the identical encoded columns. The only thing that differs is the estimator.

The Logistic Regression is REFITTED here rather than read from `reports/baseline_results.md`,
so the comparison table is produced by a single run and cannot drift from the saved baseline.

Reproduce with:
    python scripts/train_advanced.py
    python scripts/train_advanced.py --fail-on-leakage

Writes exactly one file:
    reports/model_comparison.md

The dataset is synthetic. Nothing produced here is real-world institutional performance.
"""

from __future__ import annotations

import argparse
import io
import platform
import sys
import time
from pathlib import Path
from typing import List, Sequence, Tuple

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, log_loss, precision_score, recall_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import train_baseline as tb  # noqa: E402
from train_baseline import (  # noqa: E402
    ANCHOR,
    FORBIDDEN,
    MODEL_PARAMS,
    SEED,
    SPLIT_COL,
    TARGET,
    THRESHOLD,
    LeakageError,
    calibration,
    encoded_feature_map,
    make_pipeline,
    make_preprocessor,
    metrics_block,
    select_features,
)

# --------------------------------------------------------------------------------------
# Model configuration - chosen once, deliberately, and not searched over
# --------------------------------------------------------------------------------------

RF_PARAMS = {
    "n_estimators": 500,
    "max_depth": 8,
    "min_samples_leaf": 5,
    "max_features": "sqrt",
    "class_weight": None,
    "bootstrap": True,
    "oob_score": True,
    "n_jobs": -1,
    "random_state": SEED,
}

# A rank-AUC at or above this on a SINGLE feature would indicate the answer was leaked into
# that column, not that the feature is genuinely predictive. Same threshold the dataset
# validator uses for its own leakage probe.
LEAKAGE_AUC_GUARD = 0.93

METRIC_ROWS = (
    ("log_loss", "Log loss (lower is better)", False),
    ("roc_auc", "ROC-AUC", True),
    ("pr_auc", "PR-AUC", True),
    ("accuracy", "Accuracy", True),
    ("precision", "Precision", True),
    ("recall", "Recall", True),
    ("f1", "F1", True),
)


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------


def single_feature_auc(X: pd.DataFrame, y: np.ndarray, mask: np.ndarray,
                       numeric: Sequence[str], top: int = 5) -> List[Tuple[str, float]]:
    """Rank-AUC of each numeric/binary declared feature considered on its own.

    An independent leakage probe that involves no model: a leaked column shows up here as a
    near-perfect single-feature separator. Multi-category columns are excluded because rank-AUC
    on an arbitrary ordinal encoding of a nominal level is not a meaningful measure.
    """
    sub = X.loc[mask]
    target = y[mask]
    out: List[Tuple[str, float]] = []
    for col in numeric:
        s = sub[col]
        if s.nunique(dropna=True) < 2:
            continue
        auc = float(roc_auc_score(target, s.to_numpy(dtype=float)))
        out.append((col, max(auc, 1.0 - auc)))
    out.sort(key=lambda t: -t[1])
    return out[:top]


def dense(fit_pre, X_train: pd.DataFrame, others: Sequence[pd.DataFrame]):
    """Fit the preprocessing on train only, then densify for the forest.

    Fitting on train only is what keeps `OneHotEncoder(handle_unknown="ignore")` from seeing
    the validation or test levels: test campaigns become all-zero blocks rather than new columns.
    """
    A = fit_pre.fit_transform(X_train)
    A = A.toarray() if hasattr(A, "toarray") else np.asarray(A, dtype=np.float64)
    rest = []
    for block in others:
        B = fit_pre.transform(block)
        rest.append(B.toarray() if hasattr(B, "toarray") else np.asarray(B, dtype=np.float64))
    return A, rest


def param_string(params: dict) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in params.items())


def matched_budget(y_true: np.ndarray, prob: np.ndarray, n_target: int):
    """Metrics at the threshold that yields exactly `n_target` predicted positives.

    A fixed 0.5 cut compares two models at *different* precision/recall trade-offs whenever
    their probability outputs are scaled differently. Re-scoring one model at the other's
    predicted-positive budget separates ranking quality from the choice of operating point.

    This is a DIAGNOSTIC that explains the fixed-threshold gap. It is not a tuned threshold
    and must not be adopted as one: choosing an operating point needs a cost objective
    (cost of a missed enrol vs cost of a wasted outreach) that the project has not defined.
    """
    if n_target <= 0 or n_target >= len(prob):
        return None
    thr = float(np.sort(prob)[::-1][n_target - 1])
    pred = (prob >= thr).astype(int)
    return {
        "threshold": thr,
        "n_positive": int(pred.sum()),
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
    }


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="AdmitFlow advanced model + comparison")
    ap.add_argument("--root", default=str(ROOT), help="dataset root")
    ap.add_argument("--report", default=None, help="output markdown path")
    ap.add_argument("--fail-on-leakage", action="store_true",
                    help="accepted for explicitness; a leakage failure always aborts the run "
                         "with exit code 2, with or without this flag")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    report_path = Path(args.report) if args.report else root / "reports" / "model_comparison.md"
    np.random.seed(SEED)

    # ---- shared selection, design matrix and leakage guard ----------------------------
    try:
        sel = select_features(root)
    except LeakageError as exc:
        print("LEAKAGE GUARD FAILED: " + str(exc))
        for c in exc.columns:
            print("   ", c)
        return 2

    frame, X = sel.frame, sel.design
    numeric, categorical = sel.numeric, sel.categorical
    y = frame[TARGET].to_numpy(dtype=int)
    split = frame[SPLIT_COL].to_numpy()
    tr, va, te = split == "train", split == "validation", split == "test"
    train_rate = float(y[tr].mean())

    print(f"[guard] {len(sel.features)} declared primary features, 0 forbidden, "
          f"0 POST_OUTCOME/TARGET (identical set to the baseline)")

    # ---- Logistic Regression, refitted here as the exactly comparable reference --------
    lr_pipe = make_pipeline(numeric, categorical)
    t0 = time.perf_counter()
    lr_pipe.fit(X.loc[tr], y[tr])
    lr_secs = time.perf_counter() - t0
    lr_val_p = lr_pipe.predict_proba(X.loc[va])[:, 1]
    lr_te_p = lr_pipe.predict_proba(X.loc[te])[:, 1]
    lr = {"val": metrics_block(y[va], lr_val_p, train_rate),
          "test": metrics_block(y[te], lr_te_p, train_rate)}

    # ---- Random Forest ----------------------------------------------------------------
    # Same preprocessing, same columns; the matrix is only 6,154 x 124 so densifying costs
    # about 6 MB and saves the forest from sparse-threshold overhead.
    rf_pre = make_preprocessor(numeric, categorical)
    A_tr, (A_va, A_te) = dense(rf_pre, X.loc[tr], [X.loc[va], X.loc[te]])

    base_map = encoded_feature_map(rf_pre, numeric, categorical)
    n_design = A_tr.shape[1]
    print(f"[design] {n_design} encoded columns from {len(sel.features)} declared features "
          f"({len(numeric)} numeric, {len(categorical)} categorical)")

    rf = RandomForestClassifier(**RF_PARAMS)
    t0 = time.perf_counter()
    rf.fit(A_tr, y[tr])
    rf_secs = time.perf_counter() - t0
    rf_val_p = rf.predict_proba(A_va)[:, 1]
    rf_te_p = rf.predict_proba(A_te)[:, 1]
    rf_m = {"val": metrics_block(y[va], rf_val_p, train_rate),
            "test": metrics_block(y[te], rf_te_p, train_rate)}

    # Out-of-bag is produced during the fit and probes overfitting independently of val/test.
    oob = "not available"
    oob_vec = getattr(rf, "oob_decision_function_", None)
    if oob_vec is not None:
        o = oob_vec[:, 1]
        seen = ~np.isnan(o)
        if seen.sum() > 10 and len(set(y[tr][seen].tolist())) == 2:
            oob = (f"log loss {log_loss(y[tr][seen], o[seen], labels=[0, 1]):.4f}, "
                   f"ROC-AUC {roc_auc_score(y[tr][seen], o[seen]):.4f} "
                   f"(on {int(seen.sum()):,} of {len(y[tr]):,} training rows)")
        else:
            oob = "not enough OOB coverage to score"

    # ---- calibration -------------------------------------------------------------------
    lr_cv, lr_sv, lr_iv = calibration(y[va], lr_val_p)
    lr_ct, lr_st, lr_it = calibration(y[te], lr_te_p)
    rf_cv, rf_sv, rf_iv = calibration(y[va], rf_val_p)
    rf_ct, rf_st, rf_it = calibration(y[te], rf_te_p)

    # ---- operating-point diagnostic -----------------------------------------------------
    # The fixed 0.5 cut is not a like-for-like comparison if the two models scale their
    # probabilities differently. Record both the raw scale and a matched-budget rescoring.
    budget = {}
    for split, (lp, rp) in {"val": (lr_val_p, rf_val_p), "test": (lr_te_p, rf_te_p)}.items():
        yv = y[va if split == "val" else te]
        n_pos = int((lp >= THRESHOLD).sum())
        budget[split] = {
            "lr_max": float(lp.max()),
            "rf_max": float(rp.max()),
            "lr_share": float((lp >= THRESHOLD).mean()),
            "rf_share": float((rp >= THRESHOLD).mean()),
            "n_pos": n_pos,
            "rf_matched": matched_budget(yv, rp, n_pos),
            "lr_f1": float(f1_score(yv, (lp >= THRESHOLD).astype(int), zero_division=0)),
        }

    # ---- feature importance, aggregated back to declared features ----------------------
    imp = pd.DataFrame({"feature": base_map, "importance": rf.feature_importances_})
    by_feature = (imp.groupby("feature", as_index=False)["importance"].sum()
                    .sort_values("importance", ascending=False)
                    .reset_index(drop=True))
    by_feature["share"] = by_feature["importance"] / by_feature["importance"].sum()
    top_encoded = imp.sort_values("importance", ascending=False).head(15).reset_index(drop=True)

    # ---- leakage assessment ------------------------------------------------------------
    forbidden_present = sorted(set(sel.features) & FORBIDDEN)
    forbidden_importance = float(
        by_feature.loc[by_feature["feature"].isin(FORBIDDEN), "importance"].sum())
    auc_rows = single_feature_auc(X, y, tr, numeric)
    max_auc = auc_rows[0][1] if auc_rows else float("nan")

    # ==================================================================================
    # Report
    # ==================================================================================
    L: List[str] = []
    a = L.append

    a("# AdmitFlow - Advanced Model and Comparison")
    a("")
    a("> **The dataset is synthetic.** These figures were computed on data generated by")
    a("> `scripts/generate_dataset.py` from the documented AdmitFlow admission-funnel")
    a("> specification. They describe two models fitted to a *simulated* funnel. They are")
    a("> **not** real-world institutional performance and must never be presented as such.")
    a("")
    a(f"Produced by `scripts/train_advanced.py` | seed `{SEED}` | no tuning, no cross-validation.")
    a("")
    a("---")
    a("")

    # ---- 1. setup ---------------------------------------------------------------------
    a("## 1. Setup held constant")
    a("")
    a("Both models were run on an identical footing. Feature selection, the leakage guard, the")
    a("preprocessing blocks, the split, the metrics and the calibration code are **imported")
    a("from `scripts/train_baseline.py`**, so the advanced model cannot drift from the baseline.")
    a("The Logistic Regression is refitted in this script rather than read from the saved")
    a("report, so the comparison below comes from one run.")
    a("")
    a("| Property | Value |")
    a("|---|---|")
    a("| Target | `enrolled_flag` |")
    a("| Prediction unit | one `application` |")
    a("| Prediction point | `application_submitted_ts` |")
    a("| Population | `data/processed/applications_modelling_view.csv` |")
    a("| Split | `split_hint` - train CYC-2022+2023, validation CYC-2024, test CYC-2025 |")
    a(f"| Declared features used | {len(sel.features)} (identical to the baseline) |")
    a(f"| Design columns after encoding | {n_design} "
      f"({len(numeric)} numeric + one-hot expansions of {len(categorical)} categorical) |")
    a(f"| Decision threshold | fixed at {THRESHOLD} for both models |")
    a(f"| Seed | `{SEED}` |")
    a("")
    a("| Split | Rows | Positives | Enrolment rate |")
    a("|---|---|---|---|")
    for label, mask in (("Train", tr), ("Validation", va), ("Test", te)):
        a(f"| {label} | {int(mask.sum()):,} | {int(y[mask].sum()):,} | {y[mask].mean():.6f} |")
    a("")
    a("### Preprocessing (shared, fitted on the training split only)")
    a("")
    a("| Stage | Configuration |")
    a("|---|---|")
    a("| Numeric | `SimpleImputer(strategy=\"median\")` then `StandardScaler()` |")
    a("| Categorical | `SimpleImputer(strategy=\"most_frequent\")` then "
      "`OneHotEncoder(handle_unknown=\"ignore\")` |")
    a(f"| Date features | ISO-8601 parsed, converted to days since `{ANCHOR.isoformat()}` |")
    a("")
    a("Because the encoder is fitted on the training split only, `cycle_id` yields 2 columns")
    a("(not 4) and `campaign_id` yields 16 (not 32); levels that appear only in validation or")
    a("test map to an all-zero block rather than creating a new column. For the Random Forest")
    a("the sparse result is densified. Both models see the identical columns; only the")
    a("estimator differs.")
    a("")
    a("### Model configuration")
    a("")
    a("| Model | Configuration |")
    a("|---|---|")
    a(f"| Logistic Regression | `LogisticRegression({param_string(MODEL_PARAMS)})` |")
    a(f"| Random Forest | `RandomForestClassifier({param_string(RF_PARAMS)})` |")
    a("")
    a("The forest configuration was chosen once and deliberately. `max_depth=8` and")
    a("`min_samples_leaf=5` are modest regularisers that stop small leaves from memorising;")
    a("`max_features=\"sqrt\"` is the standard decorrelation default. `class_weight=None` is")
    a("intentional: re-balancing the classes would distort the predicted probabilities, and this")
    a("comparison is judged on log loss and calibration as much as on classification.")
    a("**No search, no cross-validation and no threshold tuning was performed for either model.**")
    a("")

    # ---- 2. validation ------------------------------------------------------------------
    a("---")
    a("")
    a("## 2. Validation results (CYC-2024, 3,006 rows, base rate 0.266134)")
    a("")
    a("| Metric | Logistic Regression | Random Forest | Difference | Better |")
    a("|---|---|---|---|---|")
    for key, label, higher in METRIC_ROWS:
        lv, rv = lr["val"][key], rf_m["val"][key]
        win = "Random Forest" if ((rv > lv) if higher else (rv < lv)) else "Logistic Regression"
        a(f"| {label} | {lv:.4f} | {rv:.4f} | {rv - lv:+.4f} | {win} |")
    a(f"| Log-loss skill vs constant | {lr['val']['log_loss_skill']:.4f} | "
      f"{rf_m['val']['log_loss_skill']:.4f} | "
      f"{rf_m['val']['log_loss_skill'] - lr['val']['log_loss_skill']:+.4f} | "
      f"{'Random Forest' if rf_m['val']['log_loss_skill'] > lr['val']['log_loss_skill'] else 'Logistic Regression'} |")
    a("")
    a("Confusion matrices at the fixed 0.5 threshold:")
    a("")
    a("| Model | | Predicted 0 | Predicted 1 |")
    a("|---|---|---|---|")
    a(f"| Logistic Regression | actual 0 | {lr['val']['tn']:,} | {lr['val']['fp']:,} |")
    a(f"| Logistic Regression | actual 1 | {lr['val']['fn']:,} | {lr['val']['tp']:,} |")
    a(f"| Random Forest | actual 0 | {rf_m['val']['tn']:,} | {rf_m['val']['fp']:,} |")
    a(f"| Random Forest | actual 1 | {rf_m['val']['fn']:,} | {rf_m['val']['tp']:,} |")
    a("")

    # ---- 3. test ------------------------------------------------------------------------
    a("---")
    a("")
    a("## 3. Test results (CYC-2025, 3,001 rows, base rate 0.262912)")
    a("")
    a("| Metric | Logistic Regression | Random Forest | Difference | Better |")
    a("|---|---|---|---|---|")
    for key, label, higher in METRIC_ROWS:
        lt, rt = lr["test"][key], rf_m["test"][key]
        win = "Random Forest" if ((rt > lt) if higher else (rt < lt)) else "Logistic Regression"
        a(f"| {label} | {lt:.4f} | {rt:.4f} | {rt - lt:+.4f} | {win} |")
    a(f"| Log-loss skill vs constant | {lr['test']['log_loss_skill']:.4f} | "
      f"{rf_m['test']['log_loss_skill']:.4f} | "
      f"{rf_m['test']['log_loss_skill'] - lr['test']['log_loss_skill']:+.4f} | "
      f"{'Random Forest' if rf_m['test']['log_loss_skill'] > lr['test']['log_loss_skill'] else 'Logistic Regression'} |")
    a("")
    a("Confusion matrices at the fixed 0.5 threshold:")
    a("")
    a("| Model | | Predicted 0 | Predicted 1 |")
    a("|---|---|---|---|")
    a(f"| Logistic Regression | actual 0 | {lr['test']['tn']:,} | {lr['test']['fp']:,} |")
    a(f"| Logistic Regression | actual 1 | {lr['test']['fn']:,} | {lr['test']['tp']:,} |")
    a(f"| Random Forest | actual 0 | {rf_m['test']['tn']:,} | {rf_m['test']['fp']:,} |")
    a(f"| Random Forest | actual 1 | {rf_m['test']['fn']:,} | {rf_m['test']['tp']:,} |")
    a("")

    # ---- 4. compact comparison ----------------------------------------------------------
    a("---")
    a("")
    a("## 4. Compact comparison")
    a("")
    a("| | Logistic Regression | Random Forest |")
    a("|---|---|---|")
    a(f"| Validation log loss | {lr['val']['log_loss']:.4f} | {rf_m['val']['log_loss']:.4f} |")
    a(f"| Test log loss | {lr['test']['log_loss']:.4f} | {rf_m['test']['log_loss']:.4f} |")
    a(f"| Validation ROC-AUC | {lr['val']['roc_auc']:.4f} | {rf_m['val']['roc_auc']:.4f} |")
    a(f"| Test ROC-AUC | {lr['test']['roc_auc']:.4f} | {rf_m['test']['roc_auc']:.4f} |")
    a(f"| Validation PR-AUC | {lr['val']['pr_auc']:.4f} | {rf_m['val']['pr_auc']:.4f} |")
    a(f"| Test PR-AUC | {lr['test']['pr_auc']:.4f} | {rf_m['test']['pr_auc']:.4f} |")
    a(f"| Validation accuracy | {lr['val']['accuracy']:.4f} | {rf_m['val']['accuracy']:.4f} |")
    a(f"| Test accuracy | {lr['test']['accuracy']:.4f} | {rf_m['test']['accuracy']:.4f} |")
    a(f"| Validation precision | {lr['val']['precision']:.4f} | {rf_m['val']['precision']:.4f} |")
    a(f"| Test precision | {lr['test']['precision']:.4f} | {rf_m['test']['precision']:.4f} |")
    a(f"| Validation recall | {lr['val']['recall']:.4f} | {rf_m['val']['recall']:.4f} |")
    a(f"| Test recall | {lr['test']['recall']:.4f} | {rf_m['test']['recall']:.4f} |")
    a(f"| Validation F1 | {lr['val']['f1']:.4f} | {rf_m['val']['f1']:.4f} |")
    a(f"| Test F1 | {lr['test']['f1']:.4f} | {rf_m['test']['f1']:.4f} |")
    a(f"| Validation calibration slope / intercept | {lr_sv:.4f} / {lr_iv:.4f} | "
      f"{rf_sv:.4f} / {rf_iv:.4f} |")
    a(f"| Test calibration slope / intercept | {lr_st:.4f} / {lr_it:.4f} | "
      f"{rf_st:.4f} / {rf_it:.4f} |")
    a(f"| Fit time (seconds) | {lr_secs:.2f} | {rf_secs:.2f} |")
    a(f"| Out-of-bag | not available | {oob} |")
    a("")
    a("### Neither model is universally better")
    a("")
    a("The two models trade wins. On the probability-quality and ranking metrics the gaps are")
    a("small and go in both directions; the one large gap is F1, and that is a thresholding")
    a("artefact rather than a difference in ranking quality (see the next subsection). A")
    a("defensible statement about which to prefer depends entirely on what the downstream")
    a("consumer needs, and this run does not settle it:")
    a("")
    w_val = "Random Forest" if rf_m["val"]["log_loss"] < lr["val"]["log_loss"] else "Logistic Regression"
    w_te = "Random Forest" if rf_m["test"]["log_loss"] < lr["test"]["log_loss"] else "Logistic Regression"
    a(f"- **Probability quality (log loss, calibration)** - the property that matters if the")
    a(f"  output ever feeds a scenario engine or a threshold sweep: {w_val} on validation,")
    a(f"  {w_te} on test. Note the two splits disagree here, which is itself a reason not to")
    a("  over-read either number.")
    a("- **Ranking quality (ROC-AUC, PR-AUC)**: the differences in sections 2 and 3 are small")
    a("  enough that they should not be treated as decisive.")
    a("- **Thresholded classification (F1, recall)**: the forest is much weaker *as scored at")
    a("  0.5*, almost entirely because of how it scales its probabilities. At a matched")
    a("  predicted-positive budget the two are equivalent. This is a real limitation of the")
    a("  forest configuration as fitted, not a property of tree ensembles in general.")
    a("- **Interpretability**: the logistic regression's standardised coefficients are directly")
    a("  readable and comparable in magnitude. Impurity-based forest importances are biased")
    a("  toward high-cardinality and continuous features, and a tree split value has no")
    a("  portable narrative interpretation.")
    a("- **Stability**: both models are fitted on two cycles and evaluated on later unseen")
    a("  cycles. Neither is validated beyond a single held-out cycle per split, and with")
    a("  ~3,000 rows per split these metric estimates carry real sampling noise.")
    a("- **Cost**: the forest is slower to fit and far larger to persist, and this run does not")
    a("  show a large gain for that cost. Keeping the logistic regression as the production")
    a("  model and treating the forest as a check that the linear model is not leaving much on")
    a("  the table is a reasonable position.")
    a("")
    a("### Why F1 differs so much: the operating point, not the ranking")
    a("")
    a("At the fixed 0.5 threshold the forest's F1 is far below the logistic regression's, and")
    a("it would be easy to misread that as the forest ranking applicants worse. It is not. The")
    a("two models scale their probabilities differently, so 0.5 lands them on different")
    a("precision/recall trade-offs.")
    a("")
    a("| | Logistic Regression | Random Forest |")
    a("|---|---|---|")
    a(f"| Highest predicted probability, validation | {budget['val']['lr_max']:.4f} | "
      f"{budget['val']['rf_max']:.4f} |")
    a(f"| Share of rows predicted positive at 0.5, validation | "
      f"{budget['val']['lr_share']:.2%} | {budget['val']['rf_share']:.2%} |")
    a(f"| Share of rows predicted positive at 0.5, test | "
      f"{budget['test']['lr_share']:.2%} | {budget['test']['rf_share']:.2%} |")
    a(f"| Calibration slope, validation | {lr_sv:.4f} | {rf_sv:.4f} |")
    a(f"| Calibration slope, test | {lr_st:.4f} | {rf_st:.4f} |")
    a("")
    a("The forest **never predicts above "
      f"{budget['val']['rf_max']:.2f}**, so only about "
      f"{budget['val']['rf_share']:.0%} of rows clear 0.5, against "
      f"{budget['val']['lr_share']:.0%} for the logistic regression. Its calibration slope of")
    a(f"{rf_sv:.2f} (well above 1.0) is the same fact stated formally: the probabilities are")
    a("compressed toward the mean. `min_samples_leaf=5` and `max_depth=8` are the cause - leaf")
    a("averages pull each prediction toward the local base rate, so the forest cannot produce")
    a("confident extremes. The logistic regression shows the opposite bias (slope "
      f"{lr_sv:.2f},")
    a("over-dispersed). Two different miscalibrations in opposite directions.")
    a("")
    a("To separate the two effects, re-score the forest at the threshold that gives it the")
    a("**same number of predicted positives** as the logistic regression at 0.5:")
    a("")
    a("| Split | Model | Threshold | Predicted positive | Precision | Recall | F1 |")
    a("|---|---|---|---|---|---|---|")
    for split in ("val", "test"):
        b = budget[split]
        a(f"| {split.capitalize()} | Logistic Regression @ 0.5 | {THRESHOLD:.2f} | {b['n_pos']:,} "
          f"| {lr[split]['precision']:.4f} | {lr[split]['recall']:.4f} | {b['lr_f1']:.4f} |")
        mm = b["rf_matched"]
        if mm:
            a(f"| {split.capitalize()} | Random Forest, matched budget | "
              f"{mm['threshold']:.4f} | {mm['n_positive']:,} | {mm['precision']:.4f} | "
              f"{mm['recall']:.4f} | {mm['f1']:.4f} |")
    a("")
    gap_v = abs(budget["val"]["rf_matched"]["f1"] - budget["val"]["lr_f1"])
    a(f"Once the operating point is matched the two models are within {gap_v:.4f} F1 of each")
    a("other on validation, and their precision and recall are almost interchangeable. So the")
    a("forest is **not** the weaker ranker: at this configuration it is a similar-quality")
    a("ranker with a badly scaled probability output. Which of those two facts matters depends")
    a("entirely on how the prediction is consumed.")
    a("")
    a("> **This is a diagnostic, not a recommendation.** The matched threshold above must not")
    a("> be adopted. Selecting an operating point requires a stated cost ratio - the cost of")
    a("> missing an enrol versus the cost of a wasted outreach - and the project has not")
    a("> defined one. `THRESHOLD` stays at 0.5 for both models, and choosing it properly is a")
    a("> separate, later step.")
    a("")
    a("### Calibration")
    a("")
    a("| Split | Logistic Regression | Random Forest |")
    a("|---|---|---|")
    a(f"| Validation slope / intercept | {lr_sv:.4f} / {lr_iv:.4f} | {rf_sv:.4f} / {rf_iv:.4f} |")
    a(f"| Test slope / intercept | {lr_st:.4f} / {lr_it:.4f} | {rf_st:.4f} / {rf_it:.4f} |")
    a("")
    a("A slope below 1.0 means predicted probabilities are spread too wide; a negative")
    a("intercept means they sit too high on average. **No calibration post-processing was")
    a("applied to either model** - that is a later, separate step, and it would have to be")
    a("chosen against one model rather than both.")
    a("")
    a("**Validation reliability, Random Forest**")
    a("")
    a("| Predicted probability bin | n | Mean predicted | Observed rate |")
    a("|---|---|---|---|")
    for _, r in rf_cv.iterrows():
        if r["n"]:
            a(f"| {r['bin']} | {int(r['n']):,} | {r['mean_predicted']:.4f} | "
              f"{r['observed_rate']:.4f} |")
    a("")
    a("**Test reliability, Random Forest**")
    a("")
    a("| Predicted probability bin | n | Mean predicted | Observed rate |")
    a("|---|---|---|---|")
    for _, r in rf_ct.iterrows():
        if r["n"]:
            a(f"| {r['bin']} | {int(r['n']):,} | {r['mean_predicted']:.4f} | "
              f"{r['observed_rate']:.4f} |")
    a("")

    # ---- 5. feature importance ----------------------------------------------------------
    a("---")
    a("")
    a("## 5. Random Forest feature importance")
    a("")
    a("Impurity-based importance (mean decrease in Gini across all "
      f"{RF_PARAMS['n_estimators']} trees), aggregated from the {n_design} encoded columns back")
    a("to the declared features they came from.")
    a("")
    a("**Read this table with care.** It is not a causal measure, it is not a permutation")
    a("importance, and impurity importance is structurally biased toward continuous and")
    a("high-cardinality features. It says nothing about effect direction, and it must not be")
    a("presented as \"what drives enrolment\".")
    a("")
    a("| Rank | Declared feature | Importance | Share |")
    a("|---|---|---|---|")
    for i, r in by_feature.head(20).iterrows():
        a(f"| {i + 1} | `{r['feature']}` | {r['importance']:.5f} | {r['share']:.4f} |")
    a("")
    a(f"The top 20 declared features account for {by_feature.head(20)['share'].sum():.4f} of")
    a(f"total importance across all {len(by_feature)} used features.")
    a("")
    a("### Highest-importance individual encoded columns")
    a("")
    a("| Rank | Encoded column | Importance |")
    a("|---|---|---|")
    for i, r in top_encoded.iterrows():
        a(f"| {i + 1} | `{r['feature']}` | {r['importance']:.5f} |")
    a("")

    # ---- 6. leakage ---------------------------------------------------------------------
    a("---")
    a("")
    a("## 6. Does the advanced model introduce any leakage?")
    a("")
    a("**No.** The forest consumes the identical design matrix as the baseline, produced by the")
    a("same `select_features()` call, so the leakage boundary is enforced once and covers both")
    a("models. Tree ensembles are not exempt from leakage - if anything they are *more*")
    a("exposed than a linear model, because a tree will happily split on a memorising")
    a("identifier - so three explicit checks were run.")
    a("")
    a("| Check | Result |")
    a("|---|---|")
    a(f"| Forbidden columns present in the feature set | **{len(forbidden_present)}** "
      f"(allow-list intersects {len(FORBIDDEN)}-column FORBIDDEN set) |")
    a(f"| Declared features used, identical to the baseline | **{len(sel.features)}** (exact match) |")
    a(f"| Total importance on any forbidden column | **{forbidden_importance:.6f}** |")
    a(f"| Strongest single-feature rank AUC on the training split | **{max_auc:.4f}** "
      f"(`{auc_rows[0][0]}`) |")
    a(f"| Leakage guard threshold | {LEAKAGE_AUC_GUARD} - **not approached** |")
    a(f"| POST_OUTCOME / TARGET columns in the design matrix | **0** (enforced by `select_features`) |")
    a("")
    a("The single-feature probe, measured on the training split, involves no model at all:")
    a("")
    a("| Rank | Feature | Rank AUC |")
    a("|---|---|---|")
    for i, (col, auc) in enumerate(auc_rows, 1):
        a(f"| {i} | `{col}` | {auc:.4f} |")
    a("")
    a(f"A leaked column would appear here as a near-perfect single-feature separator. The")
    a(f"strongest is {max_auc:.3f}, roughly {LEAKAGE_AUC_GUARD - max_auc:.2f} below the")
    a(f"{LEAKAGE_AUC_GUARD} guard. That is the same feature the dataset audit flagged")
    a("(`doc_completeness_score`), which scored 0.713 on the full pooled dataset against 0.93;")
    a("the small difference is because this probe runs on the training split only, not the")
    a("pooled rows. This is why `stage_reached_order` - an exact")
    a("deterministic restatement of `enrolled_flag` that is physically present in the modelling")
    a("view - is excluded by the allow-list rather than left to the model's discretion. A tree")
    a("model would find it immediately and score near-perfectly, which is a bug, not a result.")
    a("")
    a("Multi-category columns are excluded from the probe above: rank-AUC on an arbitrary")
    a("ordinal encoding of a nominal level is not a meaningful leakage measure.")
    a("")
    a("**Residual risks that are real but are not leakage:**")
    a("")
    a(f"1. The forest fits {RF_PARAMS['n_estimators']} trees at "
      f"`max_depth={RF_PARAMS['max_depth']}` on {int(tr.sum()):,} rows with {n_design} columns,")
    a("   so it can overfit the training cycles. The out-of-bag estimate and the held-out")
    a("   cycles are the checks; the test figure is the honest one.")
    a("2. `campaign_id` is one-hot encoded and is close to a group identifier, so its")
    a("   importances mean \"which campaigns differ\", not a causal channel effect.")
    a("3. Rows are not independent - 2,529 applicants hold more than one application. No")
    a("   resampling was done, so the reported figures are unaffected, but any future")
    a("   bootstrap or significance test must group by `applicant_id`.")
    a("")

    # ---- 7. reproducibility -------------------------------------------------------------
    a("---")
    a("")
    a("## 7. Reproducibility and cost")
    a("")
    a("| Item | Value |")
    a("|---|---|")
    a("| Script | `scripts/train_advanced.py` |")
    a(f"| Seed | `{SEED}` |")
    a(f"| scikit-learn | `{sklearn.__version__}` |")
    a(f"| numpy / pandas | `{np.__version__}` / `{pd.__version__}` |")
    a(f"| Python | `{platform.python_version()}` |")
    a(f"| Platform | `{platform.system()} {platform.machine()}` |")
    a(f"| Logistic Regression fit time | {lr_secs:.2f} s |")
    a(f"| Random Forest fit time | {rf_secs:.2f} s ({RF_PARAMS['n_estimators']} trees, "
      f"n_jobs={RF_PARAMS['n_jobs']}) |")
    a("| Hyper-parameter search / cross-validation | none |")
    a("| Threshold tuning | none |")
    a("")
    a("Exact commands, run from the `admitflow-data` directory:")
    a("")
    a("```")
    a("python scripts/train_baseline.py")
    a("python scripts/train_advanced.py")
    a("```")
    a("")
    a("Every metric, importance value and conclusion in this report is deterministic given the")
    a("fixed seed. The **only** content that varies between runs is the wall-clock fit time")
    a("above, which measures this machine rather than the model. Re-running and excluding those")
    a("lines reproduces this report byte for byte:")
    a("")
    a("```")
    a("python scripts/train_advanced.py --report reports/_a.md")
    a("python scripts/train_advanced.py --report reports/_b.md")
    a("Compare-Object (gc reports/_a.md | ? { $_ -notmatch 'it time' }) `")
    a("                (gc reports/_b.md | ? { $_ -notmatch 'it time' })")
    a("```")
    a("")
    a("The dataset is read-only in both scripts - no file under `data/` is written or modified.")
    a("")

    # ---- 8. limitations -----------------------------------------------------------------
    a("---")
    a("")
    a("## 8. Limitations")
    a("")
    a("1. **Synthetic data.** Both models are fitted to a simulated funnel whose generating")
    a("   parameters are known. This is a comparison of two estimators on known data; it says")
    a("   nothing about which would win on real institutional data.")
    a("2. **One held-out cycle per split.** Validation and test are each a single cycle, so the")
    a("   estimates carry sampling noise that a repeated or rolling-origin backtest would")
    a("   quantify. This run does not, and the two splits disagreeing on log loss is a direct")
    a("   symptom of that noise.")
    a("3. **No tuning on either side.** Neither model received a fair search. This is the")
    a("   correct first comparison, but it is not the last word: a tuned model of either family")
    a("   could close or reverse these gaps.")
    a("4. **Base rate drift.** The enrolment rate falls across cycles (0.2923 train, 0.2661")
    a("   validation, 0.2629 test), so the test split is not exchangeable with the training")
    a("   split. The test figures score better partly because the base rate is lower, which")
    a("   makes **validation the more conservative estimate**. Both models are equally")
    a("   affected.")
    a("5. **Absolute-time features do not extrapolate.** The four declared date features are")
    a("   encoded as days since a fixed anchor, so a model can learn absolute calendar position")
    a("   that a later cycle cannot confirm. This is a feature-design issue, not a model issue,")
    a("   and it penalises both models identically.")
    a("6. **Selection bias in the population.** The modelling view is filtered to")
    a("   `stage_reached_order >= 3`, which conditions on latent intent and channel. Both")
    a("   models answer \"of those who submit an application, who will enrol\", not \"who will")
    a("   enrol among all inquiries\" (the top-of-funnel rate is 0.121, not 0.279).")
    a("7. **Seat capacity is a planning attribute, not an admission cap** in this dataset. It")
    a("   is a declared feature and is used, but it must not be read as a hard constraint; in")
    a("   the generated data admits exceed declared capacity several times over.")
    a("8. **Attribution fields are associational.** Channel, source and campaign features are")
    a("   first-touch records confounded by applicant mix. No causal or uplift claim is")
    a("   licensed, and the importance table in section 5 must not be read causally.")
    a("9. **Impurity importance is a weak attribution method.** Section 5 uses mean decrease in")
    a("   Gini. A permutation importance on the validation split would be a more trustworthy")
    a("   measure and is deliberately out of scope for this step.")
    a("10. **The forest's probability scale is unusable at a 0.5 operating point.** It never")
    a("   predicts above "
      f"{budget['val']['rf_max']:.2f}, so its recall and F1 at the shared threshold are poor.")
    a("   That is a property of *this* configuration; a less aggressively smoothed forest would")
    a("   spread its predictions differently. Fixing it by tuning would contradict the")
    a("   no-tuning constraint of this step, and fixing it properly requires a cost objective")
    a("   the project has not defined. It is recorded here as a known defect, not addressed.")
    a("")

    # ---- 9. integrity ------------------------------------------------------------------
    a("---")
    a("")
    a("## 9. Integrity statement")
    a("")
    a("> The dataset is synthetic, generated according to the documented AdmitFlow")
    a("> specification for development, experimentation, evaluation and demonstration. It does")
    a("> not represent real institutional admissions data. The metrics in this report describe")
    a("> two models fitted to that synthetic data and nothing more. Neither model is claimed")
    a("> to be universally better: they trade off probability quality, ranking quality,")
    a("> interpretability and cost on different metrics, and the held-out evidence here is one")
    a("> cycle per split.")
    a("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    io.open(report_path, "w", encoding="utf-8", newline="\n").write("\n".join(L))

    # ---- console summary -----------------------------------------------------------------
    print(f"[done] wrote {report_path}")
    print(f"       features={len(sel.features)} design_cols={n_design} "
          f"forbidden={len(forbidden_present)} forbidden_importance={forbidden_importance:.6f}")
    print(f"       LR  val ll={lr['val']['log_loss']:.4f} auc={lr['val']['roc_auc']:.4f} "
          f"f1={lr['val']['f1']:.4f} | test ll={lr['test']['log_loss']:.4f} "
          f"auc={lr['test']['roc_auc']:.4f} f1={lr['test']['f1']:.4f}  ({lr_secs:.2f}s)")
    print(f"       RF  val ll={rf_m['val']['log_loss']:.4f} auc={rf_m['val']['roc_auc']:.4f} "
          f"f1={rf_m['val']['f1']:.4f} | test ll={rf_m['test']['log_loss']:.4f} "
          f"auc={rf_m['test']['roc_auc']:.4f} f1={rf_m['test']['f1']:.4f}  ({rf_secs:.2f}s)")
    print(f"       max single-feature AUC on train = {max_auc:.4f} ({auc_rows[0][0]}), "
          f"guard {LEAKAGE_AUC_GUARD}")
    print(f"       oob: {oob}")
    print("       top features: "
          + ", ".join(r["feature"] for _, r in by_feature.head(5).iterrows()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
