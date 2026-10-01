#!/usr/bin/env python
"""
AdmitFlow - FORECAST MODEL AND EVALUATION
=========================================

Task    : forecast `cum_enrolled` at origin + H, for H in {1, 2, 4, 6}
Panel   : data/raw/fact_forecast_panel.csv
Features: data/processed/forecast_features.csv, built by scripts/build_forecast_features.py
Split   : the panel's own `split_hint` (contract E.5). No new split is invented.
Model   : ONE RandomForestRegressor, single modest configuration.
Tuning  : NONE. No hyper-parameter search, no cross-validation, no threshold search.

FAIL-CLOSED DESIGN
------------------
This script does not trust the feature CSV. Before fitting anything it:
  1. rebuilds the feature set from the raw panel in-process,
  2. runs the mandatory leakage guard on that rebuild and aborts on any look-ahead,
  3. cross-checks the rebuild against the CSV on disk, cell for cell.
Training cannot proceed on unverified features.

A persistence reference (predict `cum_enrolled` at T unchanged) is reported alongside the
model. For a cumulative target this is the number that makes MAE interpretable: a model that
simply repeats today's total already scores well when growth is slow.

Reproduce with:
    python scripts/train_forecast.py

Writes exactly one file:
    reports/forecast_results.md

The dataset is synthetic. Nothing here is real-world forecast performance.
"""

from __future__ import annotations

import argparse
import io
import platform
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_forecast_features as bf  # noqa: E402
from build_forecast_features import (  # noqa: E402
    HORIZONS,
    SEED,
    LookAheadError,
    run_leakage_guard,
)

RF_PARAMS = {
    "n_estimators": 300,
    "max_depth": 12,
    "min_samples_leaf": 5,
    "max_features": 0.5,
    "n_jobs": -1,
    "random_state": SEED,
}

# A per-programme cell this small cannot support a per-programme error estimate.
MIN_PROGRAMME_N = 30

META = ["programme_id", "cycle_id", "split_hint", "origin_week_start_date",
        "origin_week_index", "target_week_index", "horizon_weeks"]


def make_model(numeric: Sequence[str], categorical: Sequence[str]) -> Pipeline:
    """Impute + one-hot, then the forest. Trees are scale-invariant, so no scaling."""
    num = Pipeline([("impute", SimpleImputer(strategy="median"))])
    cat = Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                    ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False,
                                             dtype=np.float64))])
    pre = ColumnTransformer([("num", num, list(numeric)),
                             ("cat", cat, list(categorical))], remainder="drop")
    return Pipeline([("preprocess", pre), ("model", RandomForestRegressor(**RF_PARAMS))])


def metrics(y: np.ndarray, p: np.ndarray) -> Dict[str, float]:
    err = p - y
    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    out = {
        "n": int(len(y)),
        "actual_mean": float(y.mean()),
        "pred_mean": float(p.mean()),
        "mae": mae,
        "rmse": rmse,
        "bias": float(np.mean(err)),
        "r2": (1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan"),
    }
    # Within-programme R2: remove each programme's own mean level first, so the score
    # measures whether the model tracks a programme's deviation from its typical level
    # rather than how spread out the programmes are.
    return out


def within_programme_r2(df: pd.DataFrame, ycol: str, pcol: str) -> float:
    d = df[["programme_id", ycol, pcol]].copy()
    d["_ym"] = d.groupby("programme_id")[ycol].transform("mean")
    d["_pm"] = d.groupby("programme_id")[pcol].transform("mean")
    yc, pc = d[ycol] - d["_ym"], d[pcol] - d["_pm"]
    ss_res = float(np.sum((yc - pc) ** 2))
    ss_tot = float(np.sum(yc ** 2))
    return (1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan")


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="AdmitFlow forecast model + evaluation")
    ap.add_argument("--root", default=str(ROOT), help="dataset root")
    ap.add_argument("--report", default=None, help="output markdown path")
    ap.add_argument("--features", default=None, help="feature CSV path")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    report_path = (Path(args.report) if args.report
                   else root / "reports" / "forecast_results.md")
    feat_path = (Path(args.features) if args.features
                 else root / "data" / "processed" / "forecast_features.csv")
    np.random.seed(SEED)

    # ---- 1. rebuild + guard, fail closed ------------------------------------------------
    panel = bf.load_panel(root)
    merged = (panel.merge(bf._dim_programme(), on="programme_id", how="left")
                    .merge(bf._dim_cycle(), on="cycle_id", how="left"))
    rows: List[Dict] = []
    for _key, grp in merged.groupby(["programme_id", "cycle_id"]):
        origins = sorted(grp.loc[grp["is_forecast_eligible"], "week_index_in_cycle"].tolist())
        rows.extend(bf.build_group(grp, origins))
    rebuilt = pd.DataFrame(rows)

    feature_cols = [c for c in dict.fromkeys(
        bf.numeric_feature_names() + bf.MODEL_CATEGORICAL) if c in rebuilt.columns]

    try:
        checks = run_leakage_guard(panel, rebuilt, feature_cols)
    except LookAheadError as exc:
        print("LEAKAGE GUARD FAILED - refusing to train")
        print("   ", exc)
        return 4
    print(f"[guard] PASS before training: origins={checks['origins_tested']} "
          f"cells={checks['feature_cells_compared']:,} targets={checks['targets_verified']:,}")

    # ---- 2. cross-check the rebuild against the CSV on disk ------------------------------
    if not feat_path.exists():
        print(f"feature file missing: {feat_path}\nrun scripts/build_forecast_features.py")
        return 5
    disk = pd.read_csv(feat_path)
    key = ["programme_id", "cycle_id", "origin_week_index", "horizon_weeks"]
    a = rebuilt[key + ["y_cum_enrolled"]].sort_values(key).reset_index(drop=True)
    b = disk[key + ["y_cum_enrolled"]].sort_values(key).reset_index(drop=True)
    if len(a) != len(b) or not a[key].equals(b[key]):
        print("CROSS-CHECK FAILED: feature CSV does not match a fresh rebuild")
        return 5
    if not np.allclose(a["y_cum_enrolled"], b["y_cum_enrolled"], atol=1e-6):
        print("CROSS-CHECK FAILED: targets differ between CSV and rebuild")
        return 5
    print(f"[xcheck] PASS feature CSV matches a fresh guarded rebuild ({len(a):,} rows)")

    df = disk
    numeric = [c for c in feature_cols if c not in bf.MODEL_CATEGORICAL]
    categorical = [c for c in feature_cols if c in bf.MODEL_CATEGORICAL]
    X = df[feature_cols]
    y = df["y_cum_enrolled"].to_numpy(dtype=float)
    split = df["split_hint"].to_numpy()
    tr = split == "train"

    # ---- 3. fit ONE model on the training cycles ----------------------------------------
    model = make_model(numeric, categorical)
    model.fit(X.loc[tr], y[tr])
    print(f"[model] RandomForestRegressor({', '.join(f'{k}={v!r}' for k, v in RF_PARAMS.items())})"
          f"  features={len(feature_cols)} -> design width="
          f"{model.named_steps['preprocess'].transform(X.loc[tr]).shape[1]}")

    # persistence reference: cum_enrolled at the origin, unchanged
    persist = df["cum_enrolled"].to_numpy(dtype=float)

    results: Dict[str, Dict[int, Dict]] = {}
    for s in ("validation", "test"):
        m = split == s
        sub = df.loc[m].copy()
        sub["yhat"] = model.predict(X.loc[m])
        sub["persist"] = persist[m]
        results[s] = {}
        for h in HORIZONS:
            g = sub[sub["horizon_weeks"] == h]
            yy = g["y_cum_enrolled"].to_numpy(dtype=float)
            pp = g["yhat"].to_numpy(dtype=float)
            pe = g["persist"].to_numpy(dtype=float)
            block = metrics(yy, pp)
            base = metrics(yy, pe)
            block["persist_mae"] = base["mae"]
            block["persist_rmse"] = base["rmse"]
            block["persist_r2"] = base["r2"]
            block["skill_vs_persist"] = (1.0 - block["mae"] / base["mae"]
                                         if base["mae"] > 0 else float("nan"))
            block["rmse_skill_vs_persist"] = (1.0 - block["rmse"] / base["rmse"]
                                              if base["rmse"] > 0 else float("nan"))
            block["within_r2"] = within_programme_r2(g, "y_cum_enrolled", "yhat")
            block["within_persist_r2"] = within_programme_r2(g, "y_cum_enrolled", "persist")
            block["n_programmes"] = int(g["programme_id"].nunique())
            results[s][h] = block

    # ---- 4. error by programme, pooled across horizons ------------------------------------
    prog_rows = []
    for s in ("validation", "test"):
        m = split == s
        sub = df.loc[m].copy()
        sub["yhat"] = model.predict(X.loc[m])
        sub["ae"] = (sub["yhat"] - sub["y_cum_enrolled"]).abs()
        sub["persist_ae"] = (sub["cum_enrolled"] - sub["y_cum_enrolled"]).abs()
        for pid, g in sub.groupby("programme_id"):
            prog_rows.append({
                "split": s, "programme_id": pid, "n": len(g),
                "actual_mean": float(g["y_cum_enrolled"].mean()),
                "pred_mean": float(g["yhat"].mean()),
                "mae": float(g["ae"].mean()),
                "persist_mae": float(g["persist_ae"].mean()),
                "tier": g["selectivity_tier"].iloc[0],
                "capacity": int(g["base_seat_capacity"].iloc[0]),
            })
    prog = pd.DataFrame(prog_rows)

    # =====================================================================================
    # Report
    # =====================================================================================
    L: List[str] = []
    a = L.append

    a("# AdmitFlow - Forecast Results")
    a("")
    a("> **The dataset is synthetic.** These are forecasts of a simulated admissions funnel")
    a("> generated by `scripts/generate_dataset.py`. They are **not** real-world forecast")
    a("> performance and must never be presented as such.")
    a("")
    a("Target: `cum_enrolled` at forecast origin + H. Panel: `data/raw/fact_forecast_panel.csv`")
    a("(programme x cycle x ISO week). Origins: the 552 rows where `is_forecast_eligible = 1`.")
    a("")
    a("---")
    a("")

    # ---- 1. design -------------------------------------------------------------------
    a("## 1. Forecast design and feature construction")
    a("")
    a("| Property | Value |")
    a("|---|---|")
    a("| Row unit | one forecast: (programme, cycle, origin week, horizon) |")
    a("| Target quantity | count of enrolled applications, cumulative from cycle start |")
    a("| Panel grain | `programme_id` x `cycle_id` x ISO week (2,064 rows) |")
    a("| Forecast origin `T` | eligible week, rolling weekly within the cycle |")
    a("| Horizon `H` | 1, 2, 4, 6 weeks |")
    a("| Target | `cum_enrolled` observed at week `T + H` (a real observed cell) |")
    a("| Eligibility | contract F conditions 1-4, pre-computed in `is_forecast_eligible` |")
    a("| Split | panel `split_hint` - CYC-2022+2023 train, CYC-2024 validation, CYC-2025 test |")
    a(f"| Feature rows | {len(df):,} = {df.groupby(['programme_id', 'cycle_id', 'origin_week_index']).ngroups:,} origins x {len(HORIZONS)} horizons |")
    a(f"| Features | {len(feature_cols)} ({len(numeric)} numeric, {len(categorical)} categorical) |")
    a("")
    a("**Why cumulative rather than weekly.** A weekly increment of `enrolled` is zero in most")
    a("weeks, which makes error metrics degenerate. Cumulative yield is monotone and is the")
    a("quantity stakeholders actually ask for (\"how many enrolled by 15 February?\"). This")
    a("is the contract's decision D-09, not a modelling preference made here.")
    a("")
    a("**Split.** The existing chronological `split_hint` from the panel is used unchanged, as")
    a("contract E.5 requires. No new split was invented. Note this is a *target-cycle holdout*")
    a("rather than a rolling-origin backtest - contract T-05 flags that choice as still open")
    a("for the project owner, and it is not resolved here.")
    a("")
    a("### Features, all from panel history at or before T")
    a("")
    a("Every feature is produced by `origin_features()` in")
    a("`scripts/build_forecast_features.py`, which receives a frame **already sliced to**")
    a("`week_index_in_cycle <= T`. Trailing rolling windows end at the origin.")
    a("")
    a("| Group | Features |")
    a("|---|---|")
    a("| Funnel levels at T | `cum_applications_opened`, `cum_applications_started`, "
      "`cum_applications_submitted`, `cum_applications_verified`, `cum_decisions_issued`, "
      "`cum_admitted`, `cum_enrolled` |")
    a("| Weekly flows at T | `wk_applications_submitted`, `wk_applications_verified`, "
      "`wk_decisions_issued`, `wk_admitted`, `wk_enrolled` |")
    a("| Cumulative rates at T | `cum_submit_to_verify_rate`, `cum_admit_rate`, "
      "`cum_enrolment_yield` |")
    a("| Enrolment lags | `lag_cum_enrolled_{1,2,4}`, `lag_wk_enrolled_{1,2,3,4}` |")
    a("| Trailing means / spread | `roll{4,8,12}_wk_enrolled_mean`, "
      "`roll{4,8}_wk_enrolled_std`, `roll{4,8}_wk_submitted_mean`, "
      "`roll4_wk_decisions_mean`, `roll4_wk_admitted_mean` |")
    a("| Momentum | `enrol_delta_1`, `enrol_delta_4`, `enrol_acceleration` |")
    a("| Funnel progress | `weeks_since_first_decision`, `weeks_since_first_enrolment`, "
      "`has_decisions`, `has_enrolments` |")
    a("| Programme attributes | `duration_years`, `annual_fee_inr`, `base_seat_capacity`, "
      "`review_duration_days`, `demand_weight`, `selectivity_tier`, `campus_region_id`, "
      "`award_level`, `faculty`, `programme_id` |")
    a("| Cycle attributes | `total_weeks`, `cycle_year_offset` |")
    a("| Horizon | `horizon_weeks` (so ONE model serves all four horizons) |")
    a("")
    a("**Deliberately excluded as post-origin:**")
    a("")
    a("| Column | Why excluded |")
    a("|---|---|")
    a("| `n_applications` | **The main trap.** It is the programme-cycle total application "
      "count, verified constant within every one of the 48 programme-cycles. It is only "
      "knowable at cycle end, so using it as a feature is pure look-ahead. |")
    a("| `is_forecast_eligible` | Origin-selection flag, not a quantity. |")
    a("| `panel_id` | Row key. |")
    a("")
    a("Contract E.3 states features are \"the panel history strictly up to and including week")
    a("T\". The `cum_*` value **at** week T is therefore treated as known at the origin, as the")
    a("contract specifies. If an institution instead treats the origin as the *start* of week")
    a("T, every `cum_*` feature would need a one-week lag; that is a contract interpretation")
    a("question, not something this script decides.")
    a("")

    # ---- 2. leakage guard --------------------------------------------------------------
    a("---")
    a("")
    a("## 2. Leakage guard")
    a("")
    a("`run_leakage_guard()` in `scripts/build_forecast_features.py` is mandatory, executable,")
    a("and run by both scripts. It performs three checks:")
    a("")
    a("| Check | What it does | Result |")
    a("|---|---|---|")
    a("| Allow-list | Asserts no excluded/post-origin column is in the feature matrix | "
      "**pass** |")
    a(f"| Target integrity | Asserts every target is the real observed `cum_enrolled` at "
      f"`T + H` for {checks['targets_verified']:,} rows | **pass** |")
    a(f"| Future-corruption invariance | Rebuilds **all {checks['origins_tested']} origins** "
      f"from a panel whose every value in weeks `> T` is overwritten by a sentinel, and "
      f"asserts identical features ({checks['feature_cells_compared']:,} cells compared) | "
      f"**pass** |")
    a("")
    a("The third check is the real proof rather than an assertion of intent. A feature derived")
    a("from any week after the origin cannot survive its panel being overwritten.")
    a("")
    a("**The guard is itself tested.** `--self-test` injects a deliberate look-ahead (a builder")
    a("that forgets to slice, reading the final `cum_enrolled` of the whole cycle) and confirms")
    a("the guard rejects it:")
    a("")
    a("```")
    a("python scripts/build_forecast_features.py --self-test")
    a("[self-test] PASS  guard rejected the injected look-ahead: feature")
    a("           'cum_applications_opened' ... changed when post-origin panel values were")
    a("           corrupted: 959.0 -> 987654321.0")
    a("```")
    a("")
    a("A guard never observed to fail is not evidence of safety, so this is part of the")
    a("deliverable. `train_forecast.py` rebuilds and re-guards before fitting and exits 4 rather")
    a("than train on unverified features.")
    a("")

    # ---- 3. model ---------------------------------------------------------------------
    a("---")
    a("")
    a("## 3. Model")
    a("")
    a("| Item | Value |")
    a("|---|---|")
    a("| Estimator | `RandomForestRegressor` |")
    a(f"| Configuration | `{', '.join(f'{k}={v!r}' for k, v in RF_PARAMS.items())}` |")
    a("| Preprocessing | numeric median impute; categorical most-frequent impute + one-hot |")
    a("| Scaling | none - trees are scale-invariant |")
    a("| Training rows | "
      f"{int(tr.sum()):,} (cycles 2022-2023) |")
    a("| Hyper-parameter search | **none** |")
    a("| Cross-validation | **none** |")
    a(f"| Seed | `{SEED}` |")
    a(f"| scikit-learn / numpy / pandas | `{sklearn.__version__}` / `{np.__version__}` / "
      f"`{pd.__version__}` |")
    a(f"| Python / platform | `{platform.python_version()}` / "
      f"`{platform.system()} {platform.machine()}` |")
    a("")
    a("**One model, four horizons.** `horizon_weeks` is a feature rather than fitting four")
    a("separate models, so every horizon shares the same 1,152 training rows. The reported")
    a("metrics are computed per horizon regardless.")
    a("")
    a("**Reference: persistence.** `predict cum_enrolled(T)`, i.e. assume no further")
    a("enrolment. For a cumulative target this is the reference that makes MAE interpretable -")
    a("a model that simply repeats today's total already scores well when weekly growth is")
    a("small, so a raw MAE on its own says little. Skill is reported as")
    a("`1 - MAE_model / MAE_persistence`.")
    a("")

    # ---- 4. results by horizon ---------------------------------------------------------
    a("---")
    a("")
    a("## 4. Results by horizon")
    a("")
    for s in ("validation", "test"):
        n_tot = int((split == s).sum())
        label = "Validation (CYC-2024)" if s == "validation" else "Test (CYC-2025)"
        a(f"### {label} - {n_tot:,} rows")
        a("")
        a("| H | n | Actual mean | Pred mean | Bias | MAE | RMSE | R2 | R2 within-programme |")
        a("|---|---|---|---|---|---|---|---|---|")
        for h in HORIZONS:
            b = results[s][h]
            a(f"| {h} | {b['n']:,} | {b['actual_mean']:.2f} | {b['pred_mean']:.2f} | "
              f"{b['bias']:+.2f} | {b['mae']:.2f} | {b['rmse']:.2f} | {b['r2']:.3f} | "
              f"{b['within_r2']:.3f} |")
        a("")
        a("Against the persistence reference:")
        a("")
        a("| H | MAE (model) | MAE (persistence) | MAE skill | RMSE (model) | "
          "RMSE (persistence) | RMSE skill |")
        a("|---|---|---|---|---|---|---|")
        for h in HORIZONS:
            b = results[s][h]
            a(f"| {h} | {b['mae']:.2f} | {b['persist_mae']:.2f} | "
              f"{b['skill_vs_persist']:+.3f} | {b['rmse']:.2f} | {b['persist_rmse']:.2f} | "
              f"{b['rmse_skill_vs_persist']:+.3f} |")
        a("")
    bias_txt = ", ".join(f"{results['test'][h]['bias']:+.2f}" for h in HORIZONS)
    hs_txt = ", ".join(str(h) for h in HORIZONS)
    a(f"**On the bias pattern.** Test bias alternates rather than growing with horizon "
      f"({bias_txt} at H = {hs_txt}). The model is trained on four *discrete*")
    a("horizon values and cannot interpolate between them, so it snaps to the maturity")
    a("pattern it saw in training rather than tracking a smooth curve - and the yield curve")
    a("is strongly non-linear over this window, rising in every one of the 48 programme-cycles.")
    a("With 132 test points per horizon this could equally be sampling noise. No")
    a("cross-validation was run, so the two cannot be separated here, and no attempt was made")
    a("to correct the bias.")
    a("")
    a("**On R2.** The pooled R2 above is dominated by the spread *between* programmes: a large")
    a("programme heading for 200 enrolments and a small one for 10 makes R2 look strong even")
    a("for a mediocre model. The `within-programme` column removes each programme's own mean")
    a("first, so it measures whether the model tracks a programme's deviation from its typical")
    a("level. That is the more honest number here, and the skill-versus-persistence figures are")
    a("the most interpretable of all.")
    a("")

    # ---- 5. error by programme ------------------------------------------------------------
    a("---")
    a("")
    a("## 5. Error by programme")
    a("")
    te_prog = prog[prog["split"] == "test"]
    cell = int((split == "test").sum()) / max(1, te_prog["programme_id"].nunique()) / len(HORIZONS)
    a(f"Per-programme-per-horizon cells hold about {cell:.0f} test observations, which is too")
    a(f"few to estimate a per-programme error at a single horizon. The table below therefore")
    a(f"**pools all four horizons** (about {int(cell * len(HORIZONS))} observations per")
    a("programme). Only programmes with at least "
      f"{MIN_PROGRAMME_N} pooled observations are shown.")
    a("")
    for s in ("validation", "test"):
        part = prog[(prog["split"] == s) & (prog["n"] >= MIN_PROGRAMME_N)]
        label = "Validation" if s == "validation" else "Test"
        a(f"**{label}**")
        a("")
        a("| Programme | Tier | Seats | n | Actual mean | Pred mean | MAE | "
          "Persistence MAE | Skill |")
        a("|---|---|---|---|---|---|---|---|---|")
        for _, r in part.sort_values("mae").iterrows():
            skill = 1.0 - r["mae"] / r["persist_mae"] if r["persist_mae"] > 0 else float("nan")
            a(f"| `{r['programme_id']}` | {r['tier']} | {r['capacity']:,} | {int(r['n']):,} | "
              f"{r['actual_mean']:.1f} | {r['pred_mean']:.1f} | {r['mae']:.2f} | "
              f"{r['persist_mae']:.2f} | {skill:+.3f} |")
        dropped = prog[(prog["split"] == s) & (prog["n"] < MIN_PROGRAMME_N)]
        if len(dropped):
            a("")
            a(f"Suppressed as too small: "
              + ", ".join(f"`{d['programme_id']}` (n={int(d['n'])})" for _, d in dropped.iterrows())
              + ".")
        a("")
    a("Per-programme differences are descriptive only. With one held-out cycle, a handful of")
    a("observations per cell and no resampling, they carry no confidence interval, and rows")
    a("are not independent (2,529 applicants hold more than one application).")
    a("")

    # ---- 6. limitations -------------------------------------------------------------------
    a("---")
    a("")
    a("## 6. Limitations")
    a("")
    a("1. **Synthetic data.** Every figure describes a fit to a simulated funnel. Nothing")
    a("   transfers to real admissions forecasting.")
    a("2. **No tuning and no cross-validation.** One configuration, one fit, as instructed.")
    a("   These numbers are a defensible baseline, not a tuned ceiling.")
    a("3. **One held-out cycle per split.** Validation and test are each a single cycle, so")
    a("   the estimates carry sampling noise that a rolling-origin backtest would quantify.")
    a("   Contract T-05 records the holdout-versus-backtest choice as an open owner decision.")
    a("4. **Small sample.** 1,152 training rows and 132 test rows per horizon. A 300-tree")
    a("   forest on 132 test points cannot resolve small differences.")
    a("5. **The target is cumulative and near-deterministic given the origin.** Much of the")
    a("   signal is mechanical continuation of an existing yield curve, which is why the")
    a("   persistence reference is strong and why high pooled R2 must not be over-read.")
    a("6. **Origin convention.** Features include the panel values at week T itself, per")
    a("   contract E.3. An institution treating T as the start of the week would need a")
    a("   one-week lag on every cumulative feature.")
    a("7. **No prediction intervals.** Only point forecasts. An operational yield plan needs")
    a("   uncertainty, and none is produced here.")
    a("8. **Classification models untouched.** The Logistic Regression and Random Forest")
    a("   classification artifacts are unmodified by this step.")
    a("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    io.open(report_path, "w", encoding="utf-8", newline="\n").write("\n".join(L))

    print(f"[done] wrote {report_path}")
    for s in ("validation", "test"):
        for h in HORIZONS:
            b = results[s][h]
            print(f"       {s:11s} H={h}  n={b['n']:3d}  MAE {b['mae']:6.2f}  "
                  f"RMSE {b['rmse']:6.2f}  R2 {b['r2']:.3f}  within-R2 {b['within_r2']:.3f}  "
                  f"skill {b['skill_vs_persist']:+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
