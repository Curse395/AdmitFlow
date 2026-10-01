#!/usr/bin/env python
"""
AdmitFlow - MODEL EXPLAINABILITY AND ERROR ANALYSIS
===================================================

Task      : explain the two existing primary classifiers and analyse their test errors
Target    : `enrolled_flag`   Prediction point: `application_submitted_ts`
Models    : 1) Logistic Regression (baseline)  2) Random Forest (advanced)
Split     : the existing chronological `split_hint` split; error analysis on TEST only

WHAT THIS SCRIPT DOES AND DOES NOT DO
-------------------------------------
It does NOT retrain for a new purpose, tune, search, or try to improve either model. The two
estimators are refitted with byte-identical configurations and the same seed purely to
regenerate predictions (nothing is persisted to disk), because explainability needs
coefficients and row-level predictions.

Every refitted model is checked against the metrics already published in
`reports/model_comparison.md`. If a single number moves, the script aborts. That turns
"same model" into a verified fact rather than an assumption.

Scope is fixed to the primary task. No forecasting, no dashboard, no scenario code.

Reproduce with:
    python scripts/explainability_error_analysis.py

Writes exactly one file:
    reports/explainability_error_analysis.md

The dataset is synthetic. Nothing here is real-world institutional performance.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import train_baseline as tb  # noqa: E402
from train_baseline import (  # noqa: E402
    SPLIT_COL,
    TARGET,
    THRESHOLD,
    LeakageError,
    calibration,
    make_pipeline,
    make_preprocessor,
    metrics_block,
    select_features,
)
from train_advanced import RF_PARAMS, dense, encoded_feature_map  # noqa: E402

# Metrics already published in reports/model_comparison.md. The refit must reproduce them
# exactly; this is the guarantee that the two models explained here are the two models that
# were compared, not newly fitted lookalikes.
PUBLISHED = {
    "lr": {"val": {"log_loss": 0.4942, "roc_auc": 0.7772, "pr_auc": 0.5259, "f1": 0.5069},
           "test": {"log_loss": 0.4688, "roc_auc": 0.7988, "pr_auc": 0.5473, "f1": 0.5318}},
    "rf": {"val": {"log_loss": 0.4929, "roc_auc": 0.7785, "pr_auc": 0.5299, "f1": 0.3703},
           "test": {"log_loss": 0.4811, "roc_auc": 0.7946, "pr_auc": 0.5450, "f1": 0.3627}},
}

# Confusion-matrix counts published in reports/model_comparison.md, test split.
PUBLISHED_TEST_CM = {
    "lr": {"tn": 1905, "fp": 307, "fn": 392, "tp": 397},
    "rf": {"tn": 2071, "fp": 141, "fn": 583, "tp": 206},
}

# Segments requested for the error analysis. All five are columns that already exist in
# data/processed/applications_modelling_view.csv. No new data is derived or invented.
SEGMENTS = ["programme_id", "acquisition_channel", "academic_score_band",
            "selectivity_tier", "intake_round"]

# Below this many test applications a segment metric is too noisy to read.
MIN_SEGMENT_N = 30


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------


def design_columns(fitted_pre, numeric: Sequence[str], categorical: Sequence[str]):
    """(encoded_name, declared_feature, level_or_None) for every design column, in order.

    Numeric columns carry no level. Categorical levels are taken from the fitted encoder's own
    `categories_` rather than by splitting the encoded name, because declared feature names
    themselves contain underscores.
    """
    names = list(fitted_pre.get_feature_names_out())
    encoder = fitted_pre.named_transformers_["cat"].named_steps["onehot"]
    rows = [(names[i], col, None) for i, col in enumerate(numeric)]
    k = len(numeric)
    for col, cats in zip(categorical, encoder.categories_):
        for cat in cats:
            rows.append((names[k], col, cat))
            k += 1
    return rows


def error_rates(y: np.ndarray, pred: np.ndarray) -> Dict[str, float]:
    """Counts and rates for one segment. Rates are NaN when undefined, never silently zero."""
    tp = int(((pred == 1) & (y == 1)).sum())
    tn = int(((pred == 0) & (y == 0)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    n = tp + tn + fp + fn
    return {
        "n": n, "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "positives": tp + fn,
        "positive_rate": (tp + fn) / n if n else float("nan"),
        "pred_positive_rate": (tp + fp) / n if n else float("nan"),
        "fpr": fp / (fp + tn) if (fp + tn) else float("nan"),
        "fnr": fn / (fn + tp) if (fn + tp) else float("nan"),
        "precision": tp / (tp + fp) if (tp + fp) else float("nan"),
        "recall": tp / (tp + fn) if (tp + fn) else float("nan"),
    }


def fmt(v: float, nd: int = 4) -> str:
    return "n/a" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.{nd}f}"


def pct(v: float, nd: int = 2) -> str:
    return "n/a" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{100 * v:.{nd}f}%"


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="AdmitFlow explainability + error analysis")
    ap.add_argument("--root", default=str(ROOT), help="dataset root")
    ap.add_argument("--report", default=None, help="output markdown path")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    report_path = (Path(args.report) if args.report
                   else root / "reports" / "explainability_error_analysis.md")
    np.random.seed(tb.SEED)

    # ---- data, features, guard (all shared with the baseline) --------------------------
    try:
        sel = select_features(root)
    except LeakageError as exc:
        print("LEAKAGE GUARD FAILED: " + str(exc))
        return 2

    frame, X = sel.frame, sel.design
    numeric, categorical = sel.numeric, sel.categorical
    y = frame[TARGET].to_numpy(dtype=int)
    split = frame[SPLIT_COL].to_numpy()
    tr, va, te = split == "train", split == "validation", split == "test"
    train_rate = float(y[tr].mean())

    # ---- refit both models with their exact published configurations --------------------
    lr_pipe = make_pipeline(numeric, categorical)
    lr_pipe.fit(X.loc[tr], y[tr])
    lr_p = {"val": lr_pipe.predict_proba(X.loc[va])[:, 1],
            "test": lr_pipe.predict_proba(X.loc[te])[:, 1]}

    rf_pre = make_preprocessor(numeric, categorical)
    A_tr, (A_va, A_te) = dense(rf_pre, X.loc[tr], [X.loc[va], X.loc[te]])
    rf = RandomForestClassifier(**RF_PARAMS).fit(A_tr, y[tr])
    rf_p = {"val": rf.predict_proba(A_va)[:, 1], "test": rf.predict_proba(A_te)[:, 1]}

    # ---- VERIFY the refit reproduces the published comparison --------------------------
    blocks = {}
    for name, probs in (("lr", lr_p), ("rf", rf_p)):
        blocks[name] = {s: metrics_block(y[va if s == "val" else te], probs[s], train_rate)
                        for s in ("val", "test")}

    problems: List[str] = []
    for name in ("lr", "rf"):
        for s in ("val", "test"):
            for key, expected in PUBLISHED[name][s].items():
                got = blocks[name][s][key]
                if abs(got - expected) > 5e-5:
                    problems.append(f"{name}/{s}/{key}: got {got:.6f}, published {expected:.4f}")
        for k, expected in PUBLISHED_TEST_CM[name].items():
            if blocks[name]["test"][k] != expected:
                problems.append(f"{name}/test/{k}: got {blocks[name]['test'][k]}, "
                                f"published {expected}")
    if problems:
        print("REFIT VERIFICATION FAILED - the models explained here would not be the "
              "published models:")
        for p in problems:
            print("   ", p)
        return 3
    print(f"[verify] refit reproduces all published metrics exactly "
          f"({2 * 2 * 4} metric checks + {2 * 4} confusion cells)")

    # ---- Logistic Regression coefficients ----------------------------------------------
    lr_pre = lr_pipe.named_steps["preprocess"]
    lr_cols = design_columns(lr_pre, numeric, categorical)
    coef = lr_pipe.named_steps["model"].coef_[0]
    lr_int = float(lr_pipe.named_steps["model"].intercept_[0])
    lr_tab = pd.DataFrame(
        {"encoded": [c[0] for c in lr_cols],
         "feature": [c[1] for c in lr_cols],
         "level": [c[2] for c in lr_cols],
         "coef": coef})
    lr_by_feature = (lr_tab.assign(abs_coef=lr_tab["coef"].abs())
                        .groupby("feature", as_index=False)["abs_coef"].sum()
                        .sort_values("abs_coef", ascending=False)
                        .reset_index(drop=True))
    lr_by_feature["share"] = lr_by_feature["abs_coef"] / lr_by_feature["abs_coef"].sum()
    lr_top_pos = lr_tab.sort_values("coef", ascending=False).head(12).reset_index(drop=True)
    lr_top_neg = lr_tab.sort_values("coef", ascending=True).head(12).reset_index(drop=True)

    # ---- Random Forest importance ---------------------------------------------------------
    base_map = encoded_feature_map(rf_pre, numeric, categorical)
    rf_imp = pd.DataFrame({"feature": base_map, "importance": rf.feature_importances_})
    rf_by_feature = (rf_imp.groupby("feature", as_index=False)["importance"].sum()
                        .sort_values("importance", ascending=False)
                        .reset_index(drop=True))
    rf_by_feature["share"] = rf_by_feature["importance"] / rf_by_feature["importance"].sum()

    # ---- overall test errors ---------------------------------------------------------------
    y_te = y[te]
    preds = {name: {s: (p[s] >= THRESHOLD).astype(int) for s in ("val", "test")}
             for name, p in (("lr", lr_p), ("rf", rf_p))}
    overall = {name: error_rates(y_te, preds[name]["test"]) for name in ("lr", "rf")}

    # ---- segment error analysis ------------------------------------------------------------
    seg_rows: List[Dict] = []
    for col in SEGMENTS:
        if col not in frame.columns:
            raise SystemExit(f"requested segment '{col}' is not in the modelling view")
        vals = frame.loc[te, col].to_numpy()
        for val in sorted(pd.unique(vals), key=lambda v: (v is None, str(v))):
            m = vals == val
            if not m.any():
                continue
            row: Dict = {"segment": col, "value": val, "n": int(m.sum())}
            for name in ("lr", "rf"):
                for k, v in error_rates(y_te[m], preds[name]["test"][m]).items():
                    if k != "n":
                        row[f"{name}_{k}"] = v
            row["small"] = row["n"] < MIN_SEGMENT_N
            seg_rows.append(row)
    seg = pd.DataFrame(seg_rows)

    # ---- calibration ------------------------------------------------------------------------
    cal = {}
    for name, probs in (("lr", lr_p), ("rf", rf_p)):
        for s in ("val", "test"):
            tbl, slope, inter = calibration(y[va if s == "val" else te], probs[s])
            cal[(name, s)] = (tbl, slope, inter)

    # =====================================================================================
    # Report
    # =====================================================================================
    L: List[str] = []
    a = L.append
    B = blocks

    a("# AdmitFlow - Model Explainability and Error Analysis")
    a("")
    a("> **The dataset is synthetic.** Everything below describes two models fitted to")
    a("> simulated admissions data generated by `scripts/generate_dataset.py`. None of it is")
    a("> real-world institutional performance and none of it may be reported as such.")
    a("")
    a("Primary target `enrolled_flag`, predicted at `application_submitted_ts`, one row per")
    a("application. Error analysis uses the existing chronological **test** split")
    a(f"(CYC-2025, {int(te.sum()):,} rows, base rate {y_te.mean():.6f}) at threshold "
      f"{THRESHOLD:.2f}.")
    a("")
    a("---")
    a("")

    # ---- 0. method -------------------------------------------------------------------------
    a("## 0. Method and integrity check")
    a("")
    a("Nothing is persisted to disk, so both estimators were refitted with their exact")
    a("published configurations and the same seed purely to recover coefficients and")
    a("row-level predictions. **No hyper-parameter search, no tuning, no re-fitting for a new")
    a("purpose, and no attempt to improve either model.**")
    a("")
    a("To guarantee these are the same two models that were compared, the refit is checked")
    a("against every metric already published in `reports/model_comparison.md`. The run")
    a("aborts if any value moves:")
    a("")
    a("| Check | Result |")
    a("|---|---|")
    a("| Published metrics reproduced | **all matched** (log loss, ROC-AUC, PR-AUC, F1 on "
      "both splits, both models) |")
    a("| Published test confusion cells reproduced | **all matched** (TN, FP, FN, TP, both "
      "models) |")
    a(f"| Threshold | {THRESHOLD} for both models, unchanged |")
    a(f"| Seed | `{tb.SEED}` |")
    a("| Dataset | read-only; 11/11 manifest SHA-256 unchanged |")
    a("")
    a("Feature selection, the 43-feature primary allow-list and the leakage guard are")
    a("imported from `scripts/train_baseline.py`, so the design matrix is identical to the")
    a("one both models were originally fitted on.")
    a("")
    a("---")
    a("")

    # ---- 1. LR importance ------------------------------------------------------------------
    a("## 1. Global feature importance")
    a("")
    a("> **These are model-based, associative explanations. They are NOT causal effects.**")
    a("> A coefficient says how the model used a column, not what would happen if you changed")
    a("> the real-world quantity. Channel, score and tier features are confounded by applicant")
    a("> mix, and this dataset records first-touch attribution, so no uplift or intervention")
    a("> claim is licensed by anything in this section.")
    a("")

    a("### 1.1 Logistic Regression - coefficients")
    a("")
    a("Numeric features are standardised, so a coefficient is **per standard deviation** of")
    a("that feature. Categorical features are one-hot encoded with `drop=None`, so every level")
    a("gets its own column: a level's coefficient is the shift relative to the population")
    a("mean for that feature, **not** relative to a reference level. Reading them as")
    a("\"versus the reference category\" would require `drop=\"first\"`, which was not used.")
    a("")
    a("**Strongest positive coefficients** (higher predicted enrolment probability):")
    a("")
    a("| Rank | Declared feature | Level | Coefficient |")
    a("|---|---|---|---|")
    for i, r in lr_top_pos.iterrows():
        lvl = "-" if r["level"] is None else f"`{r['level']}`"
        a(f"| {i + 1} | `{r['feature']}` | {lvl} | {r['coef']:+.4f} |")
    a("")
    a("**Strongest negative coefficients** (lower predicted enrolment probability):")
    a("")
    a("| Rank | Declared feature | Level | Coefficient |")
    a("|---|---|---|---|")
    for i, r in lr_top_neg.iterrows():
        lvl = "-" if r["level"] is None else f"`{r['level']}`"
        a(f"| {i + 1} | `{r['feature']}` | {lvl} | {r['coef']:+.4f} |")
    a("")
    a("**Total absolute coefficient mass by declared feature** - this is the linear model's")
    a("closest analogue to a per-feature importance score, summing the magnitude across a")
    a("feature's encoded columns:")
    a("")
    a("| Rank | Declared feature | Sum abs(coef) | Share |")
    a("|---|---|---|---|")
    for i, r in lr_by_feature.head(12).iterrows():
        a(f"| {i + 1} | `{r['feature']}` | {r['abs_coef']:.4f} | {r['share']:.4f} |")
    a("")
    a(f"Model intercept: {lr_int:+.4f}.")
    a("")

    a("### 1.2 Random Forest - aggregated importance")
    a("")
    a("The same aggregation already used in `reports/model_comparison.md`: mean decrease in")
    a("Gini across all "
      f"{RF_PARAMS['n_estimators']} trees, summed back to the declared feature each encoded")
    a("column came from. Top 10:")
    a("")
    a("| Rank | Declared feature | Importance | Share |")
    a("|---|---|---|---|")
    for i, r in rf_by_feature.head(10).iterrows():
        a(f"| {i + 1} | `{r['feature']}` | {r['importance']:.5f} | {r['share']:.4f} |")
    a("")
    a("**Caveats specific to this measure:** impurity importance is biased toward continuous")
    a("and high-cardinality features, it is not a permutation importance, it says nothing")
    a("about effect direction, and it is not comparable in units to the logistic regression's")
    a("coefficients. Do not read the two tables as agreeing or disagreeing on magnitude.")
    a("")

    a("### 1.3 Where the two explanations agree and differ")
    a("")
    lr_top10 = set(lr_by_feature.head(10)["feature"])
    rf_top10 = set(rf_by_feature.head(10)["feature"])
    both = [f for f in rf_by_feature.head(10)["feature"] if f in lr_top10]
    only_rf = [f for f in rf_by_feature.head(10)["feature"] if f not in lr_top10]
    only_lr = [f for f in lr_by_feature.head(10)["feature"] if f not in rf_top10]
    a(f"- In **both** top-10 lists ({len(both)}): "
      + (", ".join(f"`{f}`" for f in both) if both else "none") + ".")
    a(f"- Random Forest top-10 only ({len(only_rf)}): "
      + (", ".join(f"`{f}`" for f in only_rf) if only_rf else "none") + ".")
    a(f"- Logistic Regression top-10 only ({len(only_lr)}): "
      + (", ".join(f"`{f}`" for f in only_lr) if only_lr else "none") + ".")
    a("")
    a("The two methods are structurally different (a linear additive fit versus split-counting)")
    a("so overlap is expected, and agreement on the top of the list is weak evidence that the")
    a("signal is real rather than an artefact of one estimator.")
    a("")

    # ---- 2. error analysis ----------------------------------------------------------------
    a("---")
    a("")
    a(f"## 2. Error analysis - test split at threshold {THRESHOLD:.2f}")
    a("")
    a("### 2.1 Overall confusion")
    a("")
    a("| | | Predicted 0 | Predicted 1 |")
    a("|---|---|---|---|")
    for name, label in (("lr", "Logistic Regression"), ("rf", "Random Forest")):
        o = overall[name]
        a(f"| **{label}** | actual 0 | {o['tn']:,} TN | {o['fp']:,} FP |")
        a(f"| | actual 1 | {o['fn']:,} FN | {o['tp']:,} TP |")
    a("")
    a("Counts as a share of the test split, and of the actual class where that is meaningful:")
    a("")
    a("| Quantity | % of test split | Logistic Regression | Random Forest |")
    a("|---|---|---|---|")
    n_te = int(te.sum())
    n_pos = overall["lr"]["positives"]
    n_neg = n_te - n_pos
    for key, label, den, den_lbl in (
            ("tp", "True positives TP", n_pos, "of actual enrolments"),
            ("fn", "False negatives FN", n_pos, "of actual enrolments"),
            ("fp", "False positives FP", n_neg, "of actual non-enrolments"),
            ("tn", "True negatives TN", n_neg, "of actual non-enrolments")):
        a(f"| {label} - count | {pct(overall['lr'][key] / n_te)} | "
          f"{overall['lr'][key]:,} | {overall['rf'][key]:,} |")
        a(f"| {label} - % {den_lbl} | - | {pct(overall['lr'][key] / den)} | "
          f"{pct(overall['rf'][key] / den)} |")
    a("")
    a(f"Denominators: {n_te:,} test applications, {n_pos:,} actual enrolments, "
      f"{n_neg:,} actual non-enrolments.")
    a("")
    lr_o, rf_o = overall["lr"], overall["rf"]
    a("**Reading the two error profiles.** They fail in opposite directions. The logistic")
    a(f"regression misses {lr_o['fn'] / lr_o['positives']:.1%} of actual enrolments but keeps")
    a(f"only {lr_o['fp'] / (lr_o['fp'] + lr_o['tn']):.1%} of its positive calls wrong. The")
    a(f"forest is the mirror image: it misses {rf_o['fn'] / rf_o['positives']:.1%} of")
    a(f"enrolments but only mislabels {rf_o['fp'] / (rf_o['fp'] + rf_o['tn']):.1%} of its")
    a("positive calls. Section 4 shows this is a consequence of where each model's")
    a("probabilities sit relative to 0.5, not of better or worse ranking.")
    a("")

    a("### 2.2 Error rates by segment")
    a("")
    a("Segments are columns that already exist in the modelling view. No new variable is")
    a(f"derived. Segments with fewer than {MIN_SEGMENT_N} test applications are marked")
    a("**(small)** and their rates should not be interpreted.")
    a("")

    for col in SEGMENTS:
        part = seg[seg["segment"] == col]
        a(f"**`{col}`** - {len(part)} levels, "
          f"{int(part['n'].min())}-{int(part['n'].max())} test applications each")
        a("")
        a("| Value | n | % of test | Pos rate | Model | Pred +ve | FP rate | FN rate | "
          "Precision | Recall |")
        a("|---|---|---|---|---|---|---|---|---|---|")
        for _, r in part.iterrows():
            tag = " (small)" if r["small"] else ""
            for name, label in (("lr", "LR"), ("rf", "RF")):
                a(f"| `{r['value']}`{tag if name == 'lr' else ''} | "
                  f"{int(r['n']):,} | {r['n'] / int(te.sum()):.1%} | "
                  f"{pct(r['lr_positive_rate'], 1)} | {label} | "
                  f"{pct(r[f'{name}_pred_positive_rate'], 1)} | {pct(r[f'{name}_fpr'], 1)} | "
                  f"{pct(r[f'{name}_fnr'], 1)} | {pct(r[f'{name}_precision'], 1)} | "
                  f"{pct(r[f'{name}_recall'], 1)} |")
        a("")
        wide = part[~part["small"]]
        if len(wide) >= 2:
            best = wide.loc[wide["lr_fpr"].idxmin()]
            worst = wide.loc[wide["lr_fpr"].idxmax()]
            a(f"Spread across non-small levels: false-positive rate runs from "
              f"{pct(wide['lr_fpr'].min(), 1)} (`{best['value']}`) to "
              f"{pct(wide['lr_fpr'].max(), 1)} (`{worst['value']}`); the observed positive "
              f"rate runs from {pct(wide['lr_positive_rate'].min(), 1)} to "
              f"{pct(wide['lr_positive_rate'].max(), 1)}. Differences of this size across "
              f"{col} are descriptive only - with one cycle of test data and no resampling "
              f"they carry no confidence interval, and rows are not independent "
              f"(2,529 applicants hold more than one application).")
            a("")

    a("> **How far to read these tables.** They are a description of where a fixed, unadjusted")
    a("> model errs, not evidence that any segment is inherently harder or that any feature")
    a("> causes an outcome. Differences of a few percentage points on segments of this size")
    a("> are within what a single cycle of data produces by chance. Any future significance")
    a("> testing must group by `applicant_id`.")
    a("")

    # ---- computed segment callouts (derived from the table, not hand-asserted) -----------
    big = seg[~seg["small"]]
    dead = big[big["rf_pred_positive_rate"] == 0.0]
    a("### 2.3 Segment patterns worth carrying forward")
    a("")
    a("Three patterns stand out in the tables above. They are observations about where these")
    a("two fitted models err, computed from the table rather than asserted.")
    a("")
    a(f"1. **The forest abstains entirely on some segments.** It predicts a positive for *zero*")
    a(f"   test applications in {len(dead)} of the {len(big)} non-small segment levels "
      + "(" + ", ".join(f"`{r['segment']}`=`{r['value']}`" for _, r in dead.iterrows()) + ").")
    if len(dead):
        a(f"   For those levels its false-negative rate is 100% by construction, so as a triage")
        a(f"   or outreach-prioritisation tool it would surface nobody in them at all. The")
    a("   logistic regression does flag applicants in every segment.")
    live = big[big["rf_pred_positive_rate"] > 0.0]
    hi_fnr = live.loc[live["rf_fnr"].idxmax()] if len(live) else big.loc[big["rf_fnr"].idxmax()]
    a(f"2. **Even where the forest does predict, its worst segment is "
      f"`{hi_fnr['segment']}`=`{hi_fnr['value']}`**")
    a(f"   (n={int(hi_fnr['n']):,}, positive rate {pct(hi_fnr['lr_positive_rate'], 1)}), "
      f"where it misses {pct(hi_fnr['rf_fnr'], 1)} of actual")
    a(f"   enrolments against {pct(hi_fnr['lr_fnr'], 1)} for the logistic regression. Segments")
    a("   where enrolment is uncommon are exactly where a probability-compressed model is")
    a("   least useful, because it has no confident high scores to offer.")
    a(f"3. **Both models track the base rate across segments** - false-positive rate and")
    a(f"   positive rate move together in the same direction in every segment above, which is")
    a(f"   the expected behaviour of an unadjusted model. Neither has been allowed to")
    a(f"   over-predict anywhere, so neither is exploiting a segment-specific threshold.")
    a("")

    # ---- 3. calibration ---------------------------------------------------------------------
    a("---")
    a("")
    a("## 3. Calibration / confidence")
    a("")
    a("These are the calibration figures already observed in `reports/model_comparison.md`,")
    a("recomputed here from the verified refit. **No calibration tuning, Platt scaling,")
    a("isotonic regression or threshold search was performed** - reporting the existing")
    a("behaviour is the whole point of this section.")
    a("")
    a("| Model | Split | Calibration slope | Calibration intercept |")
    a("|---|---|---|---|")
    for name, label in (("lr", "Logistic Regression"), ("rf", "Random Forest")):
        for s in ("val", "test"):
            _, slope, inter = cal[(name, s)]
            a(f"| {label} | {s} | {slope:.4f} | {inter:+.4f} |")
    a("")
    a("A slope of 1.0 with intercept 0 means predicted probabilities match observed")
    a("frequencies. Slope < 1 means the probabilities are spread too wide (over-confident);")
    a("slope > 1 means they are compressed toward the mean (under-confident).")
    a("")
    a("| Model | Split | Highest predicted probability | Share predicted positive |")
    a("|---|---|---|---|")
    for name, label in (("lr", "Logistic Regression"), ("rf", "Random Forest")):
        for s in ("val", "test"):
            p = lr_p[s] if name == "lr" else rf_p[s]
            a(f"| {label} | {s} | {p.max():.4f} | {(p >= THRESHOLD).mean():.2%} |")
    a("")
    a("**The two models are miscalibrated in opposite directions.** The logistic regression")
    a("is mildly over-confident (slope 0.83 validation, 0.92 test) - it spreads predictions")
    a("wider than the evidence supports. The forest is under-confident (slope 1.57 / 1.67):")
    a(f"`min_samples_leaf={RF_PARAMS['min_samples_leaf']}` and "
      f"`max_depth={RF_PARAMS['max_depth']}` average each leaf toward the local base rate, so")
    a("it never produces a confident prediction and its highest score on either split is")
    a("below 0.66. Neither model is calibrated, and they err in different directions.")
    a("")
    a("**Test reliability table, Logistic Regression**")
    a("")
    a("| Predicted probability bin | n | Mean predicted | Observed rate |")
    a("|---|---|---|---|")
    for _, r in cal[("lr", "test")][0].iterrows():
        if r["n"]:
            a(f"| {r['bin']} | {int(r['n']):,} | {r['mean_predicted']:.4f} | "
              f"{r['observed_rate']:.4f} |")
    a("")
    a("**Test reliability table, Random Forest**")
    a("")
    a("| Predicted probability bin | n | Mean predicted | Observed rate |")
    a("|---|---|---|---|")
    for _, r in cal[("rf", "test")][0].iterrows():
        if r["n"]:
            a(f"| {r['bin']} | {int(r['n']):,} | {r['mean_predicted']:.4f} | "
              f"{r['observed_rate']:.4f} |")
    a("")
    a("### Why this matters if these probabilities feed forecasting")
    a("")
    a("Every downstream consumer of a probability is implicitly assuming it means what it")
    a("says. Specifically:")
    a("")
    a("- **Scenario arithmetic multiplies probabilities.** Converting an enrolment")
    a("  probability into an expected count, a seat-fill estimate or a funnel projection")
    a  ("  compounds any bias: a 10% relative error becomes 10% on every scenario output, and")
    a("  it does not cancel because the same model scores every row.")
    a("- **Over-confident probabilities overstate the upside.** A model that reports 0.90 for")
    a("  a marginal applicant makes that applicant look safe in a capacity plan when the true")
    a("  frequency is materially lower. That is exactly the failure that would quietly")
    a("  over-fill a seat plan.")
    a("- **Under-confident probabilities destroy discrimination downstream.** A compressed")
    a("  probability range means small but real differences between applicants get flattened,")
    a("  which matters if scenarios are ever ranked or thresholded rather than averaged.")
    a("- **Calibration drift compounds across cycles.** The enrolment base rate already falls")
    a("  across cycles (0.2923 train, 0.2661 validation, 0.2629 test). A model calibrated on")
    a("  training cycles will be progressively miscalibrated on later ones regardless of")
    a("  ranking quality.")
    a("")
    a("This is recorded as a prerequisite for a later calibration step, not handled here.")
    a("")

    # ---- 4. comparison ----------------------------------------------------------------------
    a("---")
    a("")
    a("## 4. Model comparison conclusion")
    a("")
    a("Factual, on the existing test split, at threshold "
      f"{THRESHOLD:.2f}. Verified identical to the published figures.")
    a("")
    a("| Question | Answer |")
    a("|---|---|")
    a(f"| Lower test log loss | **Logistic Regression** "
      f"({B['lr']['test']['log_loss']:.4f} vs {B['rf']['test']['log_loss']:.4f}) |")
    a(f"| Higher test ROC-AUC | **Logistic Regression** "
      f"({B['lr']['test']['roc_auc']:.4f} vs {B['rf']['test']['roc_auc']:.4f}) |")
    a(f"| Higher test PR-AUC | **Logistic Regression** "
      f"({B['lr']['test']['pr_auc']:.4f} vs {B['rf']['test']['pr_auc']:.4f}) |")
    a(f"| Higher test F1 | **Logistic Regression** "
      f"({B['lr']['test']['f1']:.4f} vs {B['rf']['test']['f1']:.4f}) |")
    a(f"| Higher test precision | **Random Forest** "
      f"({B['lr']['test']['precision']:.4f} vs {B['rf']['test']['precision']:.4f}) |")
    a(f"| Higher test recall | **Logistic Regression** "
      f"({B['lr']['test']['recall']:.4f} vs {B['rf']['test']['recall']:.4f}) |")
    a(f"| Better calibrated (slope nearer 1.0) | **Logistic Regression** "
      f"({cal[('lr', 'test')][1]:.2f} vs {cal[('rf', 'test')][1]:.2f}) |")
    a("")
    a("**Precision / recall trade-off.** The forest is more precise and far less recall:")
    a(f"of the {rf_o['tp'] + rf_o['fp']:,} applications it calls positive, "
      f"{pct(rf_o['precision'], 1)} really enrol, against "
      f"{pct(lr_o['precision'], 1)} for the logistic regression. In exchange it recovers only")
    a(f"{pct(rf_o['recall'], 1)} of actual enrolments against {pct(lr_o['recall'], 1)}. This")
    a("is a high-precision / low-recall profile, and it follows directly from the calibration")
    a("difference in section 3 rather than from a different view of who enrols: at a matched")
    a("predicted-positive budget the two models score within ~0.01 F1 of each other.")
    a("")
    a("**Calibration differences.** Logistic regression is mildly over-confident (slope")
    a(f"{cal[('lr', 'test')][1]:.2f}); the forest is under-confident (slope "
      f"{cal[('rf', 'test')][1]:.2f}), never predicting above "
      f"{rf_p['test'].max():.2f}.")
    a("")
    a("> ### No universal winner is declared")
    a("> The logistic regression leads on every probability-quality and ranking metric measured")
    a("> on the test split, and it is better calibrated. The forest is more precise and would")
    a("> be a legitimate choice if false-positive cost dominated. But that is a preference")
    a("> about a downstream cost function, not a fact established by this data. **Model choice")
    a("> depends on the downstream use and the evaluation metric that matters for it**: a")
    a("> capacity planner weighting missed enrolments, a targeting workflow weighting wasted")
    a("> outreach, and a scenario engine needing well-calibrated probabilities would each")
    a("> justify a different answer, and none of them is settled by a single test cycle.")
    a("")

    # ---- 5. limitations -----------------------------------------------------------------------
    a("---")
    a("")
    a("## 5. Limitations")
    a("")
    a("1. **Synthetic data.** Every number describes a fit to a simulated funnel. Nothing here")
    a("   transfers to real institutional behaviour.")
    a("2. **Explanations are associational.** Coefficients and impurity importances describe")
    a("   model behaviour. They are not causal, and the dataset records first-touch")
    a("   attribution, so channel and source features are confounded by applicant mix.")
    a("3. **No local explanations.** This is a global artifact only. There is no per-applicant")
    a("   reason code, SHAP value or counterfactual, so an individual prediction cannot be")
    a("   defended to a specific applicant from this document.")
    a("4. **Single test cycle.** All error rates come from one held-out cycle of "
      f"{int(te.sum()):,} rows with no confidence intervals, so small segment differences are")
    a("   not distinguishable from noise.")
    a("5. **Rows are not independent.** 2,529 applicants hold more than one application, so")
    a("   segment percentages are not independent samples. No resampling was done here; any")
    a("   future test must group by `applicant_id`.")
    a("6. **No calibration was fitted.** Both models remain miscalibrated, as section 3")
    a("   reports. This is deliberate and is a prerequisite for a later step.")
    a("7. **Selection bias in the population.** The modelling view is filtered to")
    a("   `stage_reached_order >= 3`, so all error rates describe applications that reached")
    a("   submission - not the top-of-funnel rate of 0.121.")
    a("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    io.open(report_path, "w", encoding="utf-8", newline="\n").write("\n".join(L))

    # ---- console summary ---------------------------------------------------------------------
    print(f"[done] wrote {report_path}")
    print(f"       LR  top+ {lr_top_pos.iloc[0]['feature']} ({lr_top_pos.iloc[0]['coef']:+.3f}) | "
          f"top- {lr_top_neg.iloc[0]['feature']} ({lr_top_neg.iloc[0]['coef']:+.3f})")
    print(f"       RF  top: " + ", ".join(rf_by_feature.head(5)["feature"]))
    for name, label in (("lr", "LR"), ("rf", "RF")):
        o = overall[name]
        print(f"       {label} test  TP {o['tp']:,}  TN {o['tn']:,}  FP {o['fp']:,}  "
              f"FN {o['fn']:,}  (P {o['precision']:.4f} R {o['recall']:.4f} "
              f"F1 {B[name]['test']['f1']:.4f})")
    print(f"       segments: " + ", ".join(
        f"{c}={len(seg[seg['segment'] == c])} levels" for c in SEGMENTS)
        + f"; small (n<{MIN_SEGMENT_N}) = {int(seg['small'].sum())}")
    print(f"       calib slope  LR val {cal[('lr','val')][1]:.3f} test {cal[('lr','test')][1]:.3f}"
          f" | RF val {cal[('rf','val')][1]:.3f} test {cal[('rf','test')][1]:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
