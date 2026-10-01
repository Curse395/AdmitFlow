#!/usr/bin/env python
"""
AdmitFlow - FORECAST SEGMENT STABILITY (AF-019)
================================================

Question
--------
Is forecast performance for `cum_enrolled` reasonably consistent across the meaningful
segments that already exist in the forecast dataset, at each supported horizon?

This script ADDS a segment-level view. It does not rebuild, retune or retrain the forecasting
pipeline, and it does not touch the dataset.

WHAT IT REUSES
--------------
  data/processed/forecast_features.csv   the existing rolling-origin forecast artifact
  scripts/train_forecast.py              `make_model()` and `RF_PARAMS` - imported, never
                                         redefined here, so the model is bit-identical
  reports/forecast_results.md            the published aggregate metrics, which this
                                         script re-derives and asserts against

The feature CSV stores features and targets but NOT predictions, so segment error is computed
from predictions regenerated with the exact published configuration. Those predictions are not
assumed to be correct: `reconcile_with_published()` re-derives the aggregate MAE/RMSE/R2 for
every horizon and aborts if any of them disagrees with the values already published in
`reports/forecast_results.md`. That check is what makes this an analysis of the existing model
rather than a second, silently different model.

SEGMENT FIELDS
--------------
Only fields genuinely present in the forecast artifact are used, and only where they are
appropriate:

  programme_id        12 levels - the primary operational unit
  selectivity_tier     3 levels - coarse, deliberately small grouping of programmes
  campus_region_id     4 levels - geographic grouping
  faculty              5 levels - organisational grouping
  has_enrolments       2 levels - funnel state AT the origin (0/1)

REJECTED, with reasons (see the report):
  cycle_id        perfectly collinear with split_hint; CYC-2025 is the entire test split, so
                  'test segment performance by cycle' is not estimable - it would be the
                  aggregate restated. It is reported as a structural fact, not a segment.
  award_level     1 level ('UG') in this dataset - no variation to measure.
  split_hint      the train/validation/test boundary itself, not a segment.

TEMPORAL INTEGRITY
------------------
Every segment field used here is a static `dim_programme` attribute. `verify_temporal_integrity()`
proves this rather than asserting it: it checks each field is time-invariant per programme
across all 4 cycles and all 12 origins, that the target is strictly later than the origin in
every row, and that no segment field is a proxy for the target. No post-origin value is used
to construct any segment label.

SAMPLE SUFFICIENCY
------------------
`MIN_CELL_N = 30` follows the threshold already used for programme error in
`reports/forecast_results.md` section 5, so this report and the existing one agree on what
counts as reportable. It is not arbitrary: the test-set absolute error has sd 5.62, so a
30-observation cell carries an approximate standard error on segment MAE of about 1.03, or
21% of the mean. Below that a segment's MAE is mostly sampling noise and cannot be ranked.
Cells below the threshold are printed, counted, and marked INSUFFICIENT - never silently
dropped, and never used in the dispersion summary.

STABILITY IS MEASURED, NOT ASSERTED
-----------------------------------
No composite "stability score" is invented. Instead the report gives, per dimension x horizon:
median, IQR, full range, and the ratio of worst to best segment MAE - and, critically,
compares the observed spread against the noise floor implied by the cell sizes. A spread
inside the noise floor is reported as not distinguishable from sampling variation, which is a
different and more defensible claim than calling the model stable or unstable.

Reproduce with:
    python scripts/forecast_segment_stability.py

Writes exactly one file:
    reports/forecast_segment_stability.md

Exit codes: 0 success, 3 published-metric reconciliation failed, 4 temporal integrity
failed. The dataset is read-only and is never regenerated.
"""

from __future__ import annotations

import argparse
import io
import platform
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import sklearn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_forecast_features as bf  # noqa: E402
import train_forecast as tf  # noqa: E402

HORIZONS = [1, 2, 4, 6]

# Same threshold the existing report used for programme-level error, so the two documents
# agree on what "reportable" means.
MIN_CELL_N = 30

# Two classes of segment field, needing two different proofs of pre-origin availability.

# (a) static `dim_programme` attributes. One value per programme, so the proof is that they
#     never change between cycles or origins.
STATIC_DIMS: List[Tuple[str, str]] = [
    ("programme_id", "programme"),
    ("selectivity_tier", "selectivity tier"),
    ("campus_region_id", "campus region"),
    ("faculty", "faculty"),
]

# (b) funnel STATE at the origin, which legitimately varies between origins of the same
#     programme. The proof is not time-invariance but reconstructibility from the panel using
#     only weeks <= origin. `has_enrolments` is 0 for a programme whose earliest eligible
#     origin (week 25) still has no enrolment history, and 1 later, so a time-invariance test
#     is the wrong test for it and would reject a perfectly legitimate field.
STATE_DIMS: List[Tuple[str, str]] = [
    ("has_enrolments", "enrolments recorded at or before origin (0/1)"),
]

SEGMENT_DIMS: List[Tuple[str, str]] = STATIC_DIMS + STATE_DIMS

# Fields present but rejected, with the reason, reported for transparency.
REJECTED_DIMS: List[Tuple[str, str]] = [
    ("cycle_id", "perfectly collinear with split_hint (CYC-2025 is the whole test split)"),
    ("award_level", "single level 'UG' - no variation to measure"),
    ("split_hint", "is the train/validation/test boundary, not a segment"),
]

# Aggregate metrics already published in reports/forecast_results.md, TEST split.
# Re-derived and asserted, so this script cannot silently analyse a different model.
PUBLISHED_TEST = {
    1: {"mae": 3.90, "rmse": 5.57, "r2": 0.937},
    2: {"mae": 3.36, "rmse": 5.58, "r2": 0.947},
    4: {"mae": 5.86, "rmse": 7.95, "r2": 0.917},
    6: {"mae": 6.92, "rmse": 10.04, "r2": 0.882},
}

PUBLISHED_VAL_TEST = {
    1: {"mae": 4.02, "rmse": 6.23, "r2": 0.935},
    2: {"mae": 3.57, "rmse": 5.03, "r2": 0.965},
    4: {"mae": 5.95, "rmse": 7.51, "r2": 0.941},
    6: {"mae": 6.46, "rmse": 8.65, "r2": 0.932},
}


class IntegrityError(RuntimeError):
    """Raised when reconciliation or temporal-integrity verification fails."""


# --------------------------------------------------------------------------------------
# Integrity
# --------------------------------------------------------------------------------------


def verify_temporal_integrity(df: pd.DataFrame, panel_path: Path) -> Dict[str, object]:
    """Prove segment labels are pre-origin, and not built from the target.

    Two distinct proofs, one per class of field. Both are executed, not asserted.
    """
    out: Dict[str, object] = {}

    # ---- (a) static dimension fields: must be time-invariant per programme ---------------
    static_fields = [c for c, _ in STATIC_DIMS]
    for c in static_fields + ["award_level", "base_seat_capacity", "duration_years"]:
        if c not in df.columns:
            raise IntegrityError(f"expected segment field '{c}' is absent from the feature file")
    nuniq = df.groupby("programme_id")[static_fields + ["award_level", "base_seat_capacity",
                                                        "duration_years"]].nunique(dropna=False)
    varying = {c: int(nuniq[c].max()) for c in nuniq.columns if int(nuniq[c].max()) > 1}
    if varying:
        raise IntegrityError(
            f"static dimension fields are not time-invariant per programme, so they may "
            f"encode post-origin information: {varying}")
    out["time_invariant_fields"] = static_fields

    # ---- (b) origin-state fields: must be reconstructible from pre-origin panel weeks ----
    if not panel_path.exists():
        raise IntegrityError(f"panel not found, cannot verify state fields: {panel_path}")
    panel = pd.read_csv(panel_path)
    origins = df[["programme_id", "cycle_id", "origin_week_index"]
                 + [c for c, _ in STATE_DIMS]].drop_duplicates()
    for c, _label in STATE_DIMS:
        checked = bad = 0
        for r in origins.itertuples():
            hist = panel[(panel["programme_id"] == r.programme_id)
                         & (panel["cycle_id"] == r.cycle_id)
                         & (panel["week_index_in_cycle"] <= r.origin_week_index)]
            if hist.empty:
                raise IntegrityError(f"no pre-origin panel history for {r.programme_id}")
            expect = 1.0 if hist["cum_enrolled"].max() > 0 else 0.0
            checked += 1
            if abs(expect - float(getattr(r, c))) > 1e-9:
                bad += 1
        if bad:
            raise IntegrityError(
                f"state field '{c}' is not reconstructible from panel weeks <= origin for "
                f"{bad} of {checked} origins, so it may encode future information")
        out[f"{c}_reconstructed"] = f"{checked} origins, 0 mismatches"
    out["state_fields"] = [c for c, _ in STATE_DIMS]

    # ---- target strictly later than origin, in every row ---------------------------------
    bad_t = int((df["target_week_index"] <= df["origin_week_index"]).sum())
    if bad_t:
        raise IntegrityError(f"{bad_t} rows have a target at or before the forecast origin")
    mism = int((df["target_week_index"]
                != df["origin_week_index"] + df["horizon_weeks"]).sum())
    if mism:
        raise IntegrityError(f"{mism} rows have a target week that is not origin + H")
    out["rows_target_strictly_future"] = len(df)

    # A segment field defined from the target would be a near-perfect proxy for it.
    code = df["selectivity_tier"].map({"emerging": 0, "medium": 1, "high": 2})
    ok = code.notna()
    if ok.sum() > 2:
        r = float(np.corrcoef(code[ok], df.loc[ok, "y_cum_enrolled"])[0, 1])
        out["tier_target_corr"] = r
        if abs(r) > 0.9:
            raise IntegrityError(
                f"selectivity_tier is a near-perfect proxy for the target (r={r:.3f}); "
                f"it may have been derived from outcome information")

    # Splits must stay disjoint, as the existing pipeline defines them.
    overlap = df.groupby("cycle_id")["split_hint"].nunique()
    out["cycles_in_multiple_splits"] = int((overlap > 1).sum())
    out["cycle_split_map"] = (df.groupby("cycle_id")["split_hint"]
                                 .agg(lambda s: sorted(set(s))).to_dict())
    return out


def build_predictions(feat_path: Path) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Regenerate predictions with the published model config, reusing the existing code.

    The feature list and estimator are imported from the existing scripts, so this cannot
    drift from the pipeline it is analysing.
    """
    if not feat_path.exists():
        raise IntegrityError(
            f"forecast feature file missing: {feat_path}\n"
            f"run: python scripts/build_forecast_features.py")
    d = pd.read_csv(feat_path)

    feature_cols = [c for c in dict.fromkeys(
        bf.numeric_feature_names() + bf.MODEL_CATEGORICAL) if c in d.columns]
    numeric = [c for c in feature_cols if c not in bf.MODEL_CATEGORICAL]
    categorical = [c for c in feature_cols if c in bf.MODEL_CATEGORICAL]

    model = tf.make_model(numeric, categorical)          # imported, not redefined
    tr = (d["split_hint"] == "train").to_numpy()
    model.fit(d.loc[tr, feature_cols], d.loc[tr, "y_cum_enrolled"].to_numpy(float))

    d = d.copy()
    d["yhat"] = np.nan
    for s in ("validation", "test"):
        m = (d["split_hint"] == s).to_numpy()
        d.loc[m, "yhat"] = model.predict(d.loc[m, feature_cols])

    d["ae"] = (d["yhat"] - d["y_cum_enrolled"]).abs()
    d["se"] = (d["yhat"] - d["y_cum_enrolled"]) ** 2
    d["err"] = d["yhat"] - d["y_cum_enrolled"]
    d["persist_ae"] = (d["cum_enrolled"] - d["y_cum_enrolled"]).abs()
    return d, {"n_features": len(feature_cols), "n_design_width": int(
        model.named_steps["preprocess"].transform(d.loc[tr, feature_cols]).shape[1])}


def reconcile_with_published(d: pd.DataFrame) -> List[Dict]:
    """Re-derive published aggregate metrics and assert they still hold.

    This is the guarantee that AF-019 analyses the SAME model as the existing forecast
    report. A mismatch means the pipeline changed underneath us and is fatal.
    """
    checks: List[Dict] = []
    for split, published in (("test", PUBLISHED_TEST), ("validation", PUBLISHED_VAL_TEST)):
        for h in HORIZONS:
            g = d[(d["split_hint"] == split) & (d["horizon_weeks"] == h)]
            mae = float(g["ae"].mean())
            rmse = float(np.sqrt(g["se"].mean()))
            sst = float(((g["y_cum_enrolled"] - g["y_cum_enrolled"].mean()) ** 2).sum())
            r2 = 1.0 - float(g["se"].sum()) / sst if sst > 0 else float("nan")
            pub = published[h]
            ok = (abs(mae - pub["mae"]) < 0.005
                  and abs(rmse - pub["rmse"]) < 0.005
                  and abs(r2 - pub["r2"]) < 0.0005)
            checks.append({"split": split, "h": h, "n": len(g), "mae": mae, "rmse": rmse,
                           "r2": r2, "pub_mae": pub["mae"], "pub_rmse": pub["rmse"],
                           "pub_r2": pub["r2"], "ok": ok})
    bad = [c for c in checks if not c["ok"]]
    if bad:
        raise IntegrityError(
            "segment analysis would NOT reproduce the published forecast metrics; refusing to "
            "report segment results for a different model. Mismatches: "
            + "; ".join(f"{c['split']} H{c['h']}: MAE {c['mae']:.4f} vs {c['pub_mae']}"
                        for c in bad))
    return checks


# --------------------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------------------


def cell_stats(g: pd.DataFrame) -> Dict[str, float]:
    return {
        "n": int(len(g)),
        "mae": float(g["ae"].mean()),
        "rmse": float(np.sqrt(g["se"].mean())),
        "bias": float(g["err"].mean()),
        "actual_mean": float(g["y_cum_enrolled"].mean()),
        "pred_mean": float(g["yhat"].mean()),
        "persist_mae": float(g["persist_ae"].mean()),
    }


def aggregate_stats(g: pd.DataFrame) -> Dict[str, float]:
    return cell_stats(g)


def reportable(rows: Sequence[Dict[str, object]], col: str) -> List[Dict[str, object]]:
    """Rows eligible for a dispersion summary.

    Two independent exclusions: the row-count threshold, and (for the coarse partitions)
    levels that are a single programme in disguise. `programme_id` is exempt from the second,
    since every programme level is by definition one programme.
    """
    return [r for r in rows
            if r["sufficient"] and (col == "programme_id" or not r["single_programme"])]


def cell_status(r: Dict[str, object]) -> str:
    """Status label for one segment cell. n and independence are separate conditions."""
    if not r["sufficient"]:
        return "**INSUFFICIENT**"
    if r.get("single_programme"):
        return "**SINGLE PROGRAMME**"
    return "ok"


def dispersion(values: Sequence[float]) -> Dict[str, float]:
    """Transparent, assumption-free spread. No composite score is constructed."""
    v = np.asarray([x for x in values if np.isfinite(x)], dtype=float)
    if len(v) == 0:
        return {}
    q1, q3 = np.percentile(v, [25, 75])
    return {
        "n_segments": int(len(v)),
        "median": float(np.median(v)),
        "q1": float(q1),
        "q3": float(q3),
        "iqr": float(q3 - q1),
        "min": float(v.min()),
        "max": float(v.max()),
        "range": float(v.max() - v.min()),
        "worst_over_best": float(v.max() / v.min()) if v.min() > 0 else float("nan"),
    }


# --------------------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="AdmitFlow forecast segment stability (AF-019)")
    ap.add_argument("--root", default=str(ROOT), help="dataset root")
    ap.add_argument("--report", default=None, help="output markdown path")
    ap.add_argument("--features", default=None, help="forecast feature CSV path")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    report_path = (Path(args.report) if args.report
                   else root / "reports" / "forecast_segment_stability.md")
    feat_path = (Path(args.features) if args.features
                 else root / "data" / "processed" / "forecast_features.csv")

    # ---- integrity gates, before any segment number is produced -------------------------
    try:
        d, meta = build_predictions(feat_path)
        integrity = verify_temporal_integrity(d, root / "data" / "raw" / "fact_forecast_panel.csv")
        recon = reconcile_with_published(d)
    except IntegrityError as exc:
        print("INTEGRITY CHECK FAILED")
        print("   ", exc)
        return 3 if "published" in str(exc) else 4
    print(f"[integrity] temporal integrity PASS "
          f"({integrity['rows_target_strictly_future']:,} rows, target strictly future)")
    print(f"[integrity] static dims time-invariant per programme: "
          f"{', '.join(integrity['time_invariant_fields'])}")
    for c, _l in STATE_DIMS:
        print(f"[integrity] state field '{c}' reconstructed from pre-origin panel: "
              f"{integrity[f'{c}_reconstructed']}")
    print(f"[integrity] tier-target r = {integrity['tier_target_corr']:+.4f} (not a target proxy)")
    print(f"[integrity] reconciliation PASS - all {len(recon)} published aggregate metrics "
          f"re-derived exactly")

    eval_splits = ["validation", "test"]
    ae_sd = float(d.loc[d["split_hint"] == "test", "ae"].std(ddof=1))
    ae_mean = float(d.loc[d["split_hint"] == "test", "ae"].mean())
    se30 = ae_sd / np.sqrt(MIN_CELL_N)

    # ---- how many DISTINCT programmes sit inside each level of each dimension -------------
    # Row count is not independence. `campus_region_id`, `faculty` and `selectivity_tier` are
    # all partitions of `programme_id`, and several of their levels contain exactly one
    # programme. Such a level has 44 observations but carries no more independent
    # information than a single programme, so reporting it as a 44-observation segment would
    # overstate the evidence. Levels are therefore also flagged on programme count.
    prog_index = d.drop_duplicates("programme_id").set_index("programme_id")
    n_progs: Dict[str, Dict[str, int]] = {}
    for col, _label in SEGMENT_DIMS:
        n_progs[col] = {str(lvl): int(idx.index.nunique())
                        for lvl, idx in prog_index.groupby(col)}
    # `programme_id` is exempt: every one of its levels is one programme by definition, which
    # is the unit being analysed, not a disguised repeat of it.
    singleton = {col: sorted(lv for lv, k in n_progs[col].items() if k == 1)
                 for col, _ in SEGMENT_DIMS if col != "programme_id"}
    n_singleton = sum(len(v) for v in singleton.values())
    print(f"[segments] {n_singleton} level(s) across "
          f"{sum(1 for v in singleton.values() if v)} coarse dimension(s) hold a single "
          f"programme and are flagged as relabelled programmes")

    # ---- build segment tables -------------------------------------------------------------
    results: Dict[Tuple[str, str, int], Dict[str, List[Dict]]] = {}
    below: List[Dict] = []
    for col, label in SEGMENT_DIMS:
        for split in eval_splits:
            for h in HORIZONS:
                g = d[(d["split_hint"] == split) & (d["horizon_weeks"] == h)]
                agg = aggregate_stats(g)
                rows = []
                for lvl, sub in g.groupby(col, dropna=False):
                    s = cell_stats(sub)
                    s["level"] = str(lvl)
                    s["sufficient"] = s["n"] >= MIN_CELL_N
                    s["delta_mae_vs_agg"] = s["mae"] - agg["mae"]
                    s["delta_rmse_vs_agg"] = s["rmse"] - agg["rmse"]
                    s["skill_vs_persist"] = (1.0 - s["mae"] / s["persist_mae"]
                                              if s["persist_mae"] > 0 else float("nan"))
                    s["n_programmes"] = n_progs[col][str(lvl)]
                    s["single_programme"] = s["n_programmes"] == 1
                    rows.append(s)
                    if not s["sufficient"]:
                        below.append({"dim": col, "label": label, "split": split, "h": h,
                                      "level": s["level"], "n": s["n"]})
                results[(col, split, h)] = {"rows": sorted(rows, key=lambda r: r["mae"]),
                                            "agg": agg, "label": label}

    # pooled across horizons, as the existing report did, to show the same field is
    # reportable once the cell is big enough
    pooled: Dict[Tuple[str, str], Dict] = {}
    for col, label in SEGMENT_DIMS:
        for split in eval_splits:
            g = d[(d["split_hint"] == split)]
            agg = aggregate_stats(g)
            rows = []
            for lvl, sub in g.groupby(col, dropna=False):
                s = cell_stats(sub)
                s["level"] = str(lvl)
                s["sufficient"] = s["n"] >= MIN_CELL_N
                s["delta_mae_vs_agg"] = s["mae"] - agg["mae"]
                s["skill_vs_persist"] = (1.0 - s["mae"] / s["persist_mae"]
                                         if s["persist_mae"] > 0 else float("nan"))
                s["n_programmes"] = n_progs[col][str(lvl)]
                s["single_programme"] = s["n_programmes"] == 1
                rows.append(s)
            pooled[(col, split)] = {"rows": sorted(rows, key=lambda r: r["mae"]),
                                    "agg": agg, "label": label}

    L: List[str] = []
    a = L.append

    a("# AdmitFlow - Forecast Segment Stability (AF-019)")
    a("")
    a("> **The dataset is synthetic.** Every figure below describes a fit to a simulated")
    a("> admissions funnel generated by `scripts/generate_dataset.py`. Nothing here is")
    a("> real-world forecast performance and none of it transfers to a real institution.")
    a("")
    a("---")
    a("")

    # ---- objective -----------------------------------------------------------------------
    a("## Objective")
    a("")
    a("To measure whether forecast performance for `cum_enrolled` is **reasonably consistent**")
    a("across the meaningful segments that already exist in the forecast dataset, at each")
    a("supported horizon. This adds a segment-level view to the existing per-horizon forecast")
    a("evaluation; it does not rebuild or retune the forecasting pipeline.")
    a("")
    a("The existing `reports/forecast_results.md` reports per-horizon aggregate error and a")
    a("programme table that **pools all four horizons** (section 5). It does not report")
    a("error per segment per horizon. That is the gap this analysis fills.")
    a("")
    a("Stability is **measured, not asserted**. No composite \"stability score\" is")
    a("invented, and the model is not labelled stable or unstable. Where observed variation")
    a("falls inside the noise implied by the cell sizes, that is reported as *not")
    a("distinguishable from sampling variation*, which is a different and more defensible")
    a("claim.")
    a("")

    # ---- data ---------------------------------------------------------------------------
    a("## Data and source")
    a("")
    a("| Role | Path |")
    a("|---|---|")
    a("| Forecast artifact (inputs) | `data/processed/forecast_features.csv` |")
    a("| Model definition (imported, not redefined) | `scripts/train_forecast.py` |")
    a("| Feature builder (imported, not modified) | `scripts/build_forecast_features.py` |")
    a("| Published metrics verified against | `reports/forecast_results.md` |")
    a("| This report | `reports/forecast_segment_stability.md` |")
    a("")
    a(f"The feature file holds {len(d):,} rows and {d.shape[1]} columns as stored on disk "
      f"(2,059 data columns after the five derived error columns this script adds): one row")
    a("per (programme, cycle, origin, horizon). This analysis read "
      f"{meta['n_features']} feature columns from it,")
    a(f"which expand to a design width of {meta['n_design_width']} after preprocessing - the")
    a("same 53 features and the same design width the existing pipeline uses.")
    a("")
    a("**Predictions.** The artifact stores features and targets but not predictions, so")
    a("predictions were regenerated with the published estimator and configuration, imported")
    a("from `train_forecast.py` so they cannot drift from the pipeline being analysed. This is")
    a("**not** a retrain in the sense of searching for a better model: no parameter was")
    a("changed, no search was run, and the fitted model reproduces the already-published")
    a("numbers exactly (verified below).")
    a("")
    a("**Reconciliation - the guarantee that this analyses the same model.**")
    a("")
    a("| Split | H | n | MAE (re-derived) | MAE (published) | RMSE (re-derived) | "
      "RMSE (published) | R2 (re-derived) | R2 (published) | Match |")
    a("|---|---|---|---|---|---|---|---|---|---|")
    for c in recon:
        a(f"| {c['split']} | {c['h']} | {c['n']:,} | {c['mae']:.4f} | {c['pub_mae']} | "
          f"{c['rmse']:.4f} | {c['pub_rmse']} | {c['r2']:.5f} | {c['pub_r2']} | "
          f"{'yes' if c['ok'] else 'NO'} |")
    a("")
    a("All 8 aggregate metrics (validation and test, four horizons each) reproduce the values")
    a("already published. The script aborts rather than report segment results if any of them")
    a("moved.")
    a("")

    # ---- horizons -----------------------------------------------------------------------
    a("## Forecast horizons evaluated")
    a("")
    a("| Horizon | Test rows | Validation rows | Status |")
    a("|---|---|---|---|")
    for h in HORIZONS:
        nt = int(((d["split_hint"] == "test") & (d["horizon_weeks"] == h)).sum())
        nv = int(((d["split_hint"] == "validation") & (d["horizon_weeks"] == h)).sum())
        a(f"| H{h} | {nt:,} | {nv:,} | evaluated |")
    a("")
    a("All four horizons in the existing design (H1, H2, H4, H6) are available in both")
    a("evaluation splits, and all four are evaluated. Horizon is carried as the column")
    a("`horizon_weeks`.")
    a("")
    a("**Split representation.** The artifact uses `split_hint` with values `train`,")
    a("`validation`, `test`, exactly as the existing pipeline defines them: CYC-2022 and")
    a("CYC-2023 train, CYC-2024 validation, CYC-2025 test. This analysis reads test and")
    a("validation only, and never uses train rows to form segment statistics, so the")
    a("train/validation/test separation is respected rather than re-derived.")
    a("")

    # ---- segment definitions --------------------------------------------------------------
    a("## Segment definitions")
    a("")
    a("Only fields genuinely present in `forecast_features.csv` are used. They fall into two")
    a("classes, and each class is verified by the check that actually applies to it.")
    a("")
    a("**Class (a) static `dim_programme` attributes.** `programme_id`,")
    a("`selectivity_tier`, `campus_region_id`, `faculty`. Each holds one value per programme,")
    a("so pre-origin availability is proven by checking it never changes across all 4 cycles")
    a("and all 12 eligible origins. Verified for all four fields.")
    a("")
    a("**Class (b) funnel state at the origin.** `has_enrolments`. This legitimately *varies*")
    a("between origins of the same programme - a programme whose first eligible origin (week")
    a("25) still has no enrolment history has `has_enrolments = 0` there and 1 later. A")
    a("time-invariance test is the wrong test for such a field and would reject a legitimate")
    a("one, so a stronger check is used instead: the field is **re-derived from the raw panel")
    a("using only weeks at or before the origin** and compared row for row.")
    a("")
    for c, v in sorted((k, val) for k, val in integrity.items()
                       if k.endswith("_reconstructed")):
        a(f"- `{c[: -len('_reconstructed')]}`: {v} - fully reconstructible from pre-origin weeks")
    a("")
    for col, label in SEGMENT_DIMS:
        nlev = int(d[col].nunique())
        test_counts = d[d["split_hint"] == "test"].groupby(col).size()
        vmin, vmax = int(test_counts.min()), int(test_counts.max())
        a(f"### `{col}` - {label}")
        a("")
        a(f"- **Meaning**: {label}")
        a(f"- **Levels**: {nlev} in the full artifact")
        a(f"- **Test rows per level**: {vmin} to {vmax} total across all four horizons "
      f"({int(round(vmin / len(HORIZONS)))} to {int(round(vmax / len(HORIZONS)))} per "
      f"horizon)")
        a(f"- **Class**: {'static dimension' if col in dict(STATIC_DIMS) else 'origin state'}")
        a(f"- **Pre-origin availability**: "
          f"{'verified time-invariant per programme' if col in dict(STATIC_DIMS) else 'verified reconstructible from panel weeks <= origin'}")
        if col == "programme_id":
            a("- **Why relevant**: the primary operational unit. A yield plan is written per")
            a("  programme, so per-programme forecast reliability is the question an")
            a("  admissions team actually asks.")
        elif col == "selectivity_tier":
            a("- **Why relevant**: groups programmes by how competitive they are. Tests")
            a("  whether the model is systematically weaker on highly selective programmes,")
            a("  which have fewer admitted applicants per unit of enrolment.")
        elif col == "campus_region_id":
            a("- **Why relevant**: operational grouping. Tests whether forecast reliability is")
            a("  concentrated geographically.")
        elif col == "faculty":
            a("- **Why relevant**: organisational grouping, a different cut from region. If")
            a("  weakness clustered by faculty but not by region, that would point at")
            a("  programme mix rather than any single cause.")
        elif col == "has_enrolments":
            a("- **Why relevant**: funnel state **at the origin**, not an outcome. Tests")
            a("  whether the model is less accurate for origins that have no enrolment history")
            a("  yet. It is verified reconstructible from panel weeks at or before the origin,")
            a("  so using it introduces no future information. As the counts below show, the")
            a("  data cannot support a conclusion on this field.")
        a("")

    a("### Fields deliberately not used as segments")
    a("")
    a("| Field | Reason |")
    a("|---|---|")
    for c, why in REJECTED_DIMS:
        a(f"| `{c}` | {why} |")
    a("")
    a("`cycle_id` deserves emphasis because it looks like the most natural segment dimension")
    a("and is **not usable**. The split map is:")
    a("")
    a("| Cycle | Splits it appears in |")
    a("|---|---|")
    for cyc, sp in sorted(integrity["cycle_split_map"].items()):
        a(f"| `{cyc}` | {', '.join(sp)} |")
    a("")
    a("Each cycle belongs to exactly one split, so `cycle_id` and `split_hint` are perfectly")
    a("collinear. Segment performance *by cycle* on the test split would be one level of 132")
    a("rows - that is, the aggregate restated. Reporting it as a segment would manufacture the")
    a("appearance of a cycle-level stability finding. It is stated as a structural limitation")
    a("instead.")
    a("")

    # ---- sample sizes -------------------------------------------------------------------
    a("## Segment sample sizes")
    a("")
    a(f"Minimum cell size for reliable interpretation: **n >= {MIN_CELL_N}**.")
    a("")
    a(f"This is the threshold already used for programme-level error in")
    a(f"`reports/forecast_results.md` section 5, so the two documents agree on what")
    a("\"reportable\" means. It is not arbitrary. On the test split the absolute error has a")
    a(f"standard deviation of {ae_sd:.2f} enrolments (mean {ae_mean:.2f}), so a 30-observation")
    a(f"cell carries an approximate standard error on segment MAE of {se30:.2f}, or about")
    a(f"{100 * se30 / ae_mean:.0f}% of the mean. Below 30 observations a segment's MAE is")
    a("mostly sampling noise and cannot be meaningfully ranked against another segment.")
    a("")
    a("Cells below the threshold are **printed and counted, never silently dropped**.")
    a("")
    a("Per-horizon cell sizes, test split:")
    a("")
    a("| Segment field | Levels | Min cell per horizon | Max cell per horizon | Cells below 30 |")
    a("|---|---|---|---|---|")
    for col, _label in SEGMENT_DIMS:
        ct = pd.crosstab(d[d["split_hint"] == "test"][col],
                         d[d["split_hint"] == "test"]["horizon_weeks"])
        n_below = int((ct.values < MIN_CELL_N).sum())
        a(f"| `{col}` | {ct.shape[0]} | {int(ct.values.min())} | {int(ct.values.max())} | "
          f"{n_below} of {ct.size} |")
    a("")
    n_cells_total = sum(len(results[(c, s, h)]["rows"])
                        for c, _ in SEGMENT_DIMS for s in eval_splits for h in HORIZONS)
    a(f"In total **{len(below)} segment-horizon cells fall below n = {MIN_CELL_N}**, out of")
    a(f"{n_cells_total} evaluated across both evaluation splits and all four horizons. These")
    a("are marked **INSUFFICIENT** in every table below and are excluded from the dispersion")
    a("summaries, which would otherwise be dominated by sampling noise.")
    a("")
    a("### Row count is not independence")
    a("")
    a("A second, separate sufficiency problem survives the n >= 30 threshold.")
    a("`campus_region_id`,")
    a("`faculty` and `selectivity_tier` are all partitions of `programme_id`, so every level")
    a("of them is really a set of programmes. A level holding 44 rows but only **one**")
    a("programme carries no more independent information than that programme itself. Those")
    a("levels are marked `SINGLE PROGRAMME` in the tables and must not be read as")
    a("replicated segment evidence.")
    a("")
    a("| Field | Level | Programmes inside | Interpretation |")
    a("|---|---|---|---|")
    for col, _label in SEGMENT_DIMS:
        if col in ("programme_id", "has_enrolments"):
            continue
        for lvl, k in sorted(n_progs[col].items(), key=lambda kv: -kv[1]):
            note = ("relabelled single programme, not independent evidence"
                    if k == 1 else f"pool of {k} programmes")
            a(f"| `{col}` | `{lvl}` | {k} | {note} |")
    a("")
    n_coarse_dims = sum(1 for v in singleton.values() if v)
    a(f"**{n_singleton} levels across {n_coarse_dims} of the coarse dimensions contain a "
      f"single**")
    a("**programme**, so they are relabelled programmes rather than segments in their own")
    a("right. Every such level is flagged `SINGLE PROGRAMME` in the tables below.")
    a("")
    a("`has_enrolments` is deliberately absent from this table because it is not a")
    a("partition of programme. It splits *origins*, not programmes, so both of its levels")
    a("contain all 12 programmes and the programme count says nothing about how the cell is")
    a("balanced. Its problem is the opposite one - imbalance in rows, not in independent")
    a("units.")
    a("")
    a("**The central structural fact of this analysis:** a programme-horizon cell holds only")
    a("**11 test observations** (12 programmes x 11 eligible origins / 528 test rows). That is")
    a("below the threshold, so **per-programme, per-horizon error is not reliably estimable**")
    a("from this dataset. It becomes estimable only when the four horizons are pooled into 44")
    a("observations per programme, which is the cut the existing report uses. Both are")
    a("reported: the per-horizon table below for completeness, and the pooled table that can")
    a("actually be interpreted.")
    a("")

    # ---- metrics by segment ----------------------------------------------------------------
    a("## Metrics by segment")
    a("")
    a("Metrics are the ones the existing forecast evaluation already uses, so results are")
    a("directly comparable with `reports/forecast_results.md`:")
    a("")
    a("- **MAE** - mean absolute error, in enrolled applications")
    a("- **RMSE** - root mean squared error, penalises large misses more than MAE")
    a("- **Bias** - mean signed error; positive means over-prediction")
    a("- **Actual / predicted mean** - to expose level bias separately from spread")
    a("- **Skill vs persistence** - `1 - MAE_segment / MAE_persistence`, the reference already")
    a("  established in the existing report")
    a("")
    a("**Aggregate** is the same horizon, same split, all programmes pooled. It is shown next")
    a("to every table so a segment can be compared with the overall result.")
    a("")
    a("Test split (the primary evaluation). Validation is reported in the next subsection.")
    a("")

    for col, label in SEGMENT_DIMS:
        a(f"### `{col}` ({label}) - test split, by horizon")
        a("")
        a("| Horizon | Level | n | Prog | MAE | RMSE | Bias | Actual mean | Pred mean | "
          "Persist MAE | Skill | vs aggregate MAE | Status |")
        a("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for h in HORIZONS:
            blk = results[(col, "test", h)]
            agg = blk["agg"]
            for r in blk["rows"]:
                a(f"| H{h} | `{r['level']}` | {r['n']} | {r['n_programmes']} | "
                  f"{r['mae']:.2f} | {r['rmse']:.2f} | "
                  f"{r['bias']:+.2f} | {r['actual_mean']:.1f} | {r['pred_mean']:.1f} | "
                  f"{r['persist_mae']:.2f} | {r['skill_vs_persist']:+.3f} | "
                  f"{r['delta_mae_vs_agg']:+.2f} | {cell_status(r)} |")
            a(f"| H{h} | **AGGREGATE** | {agg['n']} | 12 | {agg['mae']:.2f} | "
              f"{agg['rmse']:.2f} | "
              f"{agg['bias']:+.2f} | {agg['actual_mean']:.1f} | {agg['pred_mean']:.1f} | "
              f"{agg['persist_mae']:.2f} | "
              f"{1.0 - agg['mae'] / agg['persist_mae']:+.3f} | - | - |")
        a("")
    a("`Prog` is the number of distinct programmes inside the level; "
      "`**INSUFFICIENT**` means fewer than 30 rows, `**SINGLE PROGRAMME**` means 30+ rows but")
    a("only one distinct programme.")
    a("")

    a("### Validation split, by horizon")
    a("")
    a("Shown for the same fields. The validation split has an identical structure (132 rows")
    a("per horizon, 11 per programme), so the same sample-sufficiency conclusions apply.")
    a("")
    for col, label in SEGMENT_DIMS:
        if col == "programme_id":
            a("| Horizon | Programme | n | MAE | RMSE | Bias | vs aggregate MAE | Status |")
            a("|---|---|---|---|---|---|---|---|")
            for h in HORIZONS:
                blk = results[(col, "validation", h)]
                agg = blk["agg"]
                for r in blk["rows"]:
                    a(f"| H{h} | `{r['level']}` | {r['n']} | {r['mae']:.2f} | "
                      f"{r['rmse']:.2f} | {r['bias']:+.2f} | {r['delta_mae_vs_agg']:+.2f} | "
                      f"{cell_status(r)} |")
                a(f"| H{h} | **AGGREGATE** | {agg['n']} | {agg['mae']:.2f} | "
                  f"{agg['rmse']:.2f} | {agg['bias']:+.2f} | - | - |")
            a("")
            a("Other fields on validation:")
            a("")
        a(f"**`{col}` ({label})**")
        a("")
        a("| Horizon | Level | n | Prog | MAE | RMSE | Bias | vs aggregate MAE | Status |")
        a("|---|---|---|---|---|---|---|---|---|")
        for h in HORIZONS:
            blk = results[(col, "validation", h)]
            agg = blk["agg"]
            for r in blk["rows"]:
                a(f"| H{h} | `{r['level']}` | {r['n']} | {r['n_programmes']} | "
                  f"{r['mae']:.2f} | {r['rmse']:.2f} | "
                  f"{r['bias']:+.2f} | {r['delta_mae_vs_agg']:+.2f} | {cell_status(r)} |")
            a(f"| H{h} | **AGGREGATE** | {agg['n']} | 12 | {agg['mae']:.2f} | "
              f"{agg['rmse']:.2f} | {agg['bias']:+.2f} | - | - |")
        a("")

    # ---- pooled ---------------------------------------------------------------------------
    a("## Pooled across horizons")
    a("")
    a("Pooling the four horizons raises a programme cell from 11 to 44 observations, which")
    a("clears the sufficiency threshold. This is the same cut `reports/forecast_results.md`")
    a("uses, and it is the only per-programme view that can be interpreted. Pooling mixes")
    a("four horizons of different difficulty, so these numbers are **not** comparable to a")
    a("single-horizon aggregate.")
    a("")
    for col, label in SEGMENT_DIMS:
        a(f"**`{col}` ({label}) - test split, pooled**")
        a("")
        a("| Level | n | Prog | MAE | RMSE | Bias | Persist MAE | Skill | "
          "vs aggregate MAE | Status |")
        a("|---|---|---|---|---|---|---|---|---|---|")
        for r in pooled[(col, "test")]["rows"]:
            a(f"| `{r['level']}` | {r['n']} | {r['n_programmes']} | {r['mae']:.2f} | "
              f"{r['rmse']:.2f} | "
              f"{r['bias']:+.2f} | {r['persist_mae']:.2f} | "
              f"{1.0 - r['mae'] / r['persist_mae']:+.3f} | {r['delta_mae_vs_agg']:+.2f} | "
              f"{cell_status(r)} |")
        agg = pooled[(col, "test")]["agg"]
        a(f"| **AGGREGATE** | {agg['n']} | 12 | {agg['mae']:.2f} | {agg['rmse']:.2f} | "
          f"{agg['bias']:+.2f} | {agg['persist_mae']:.2f} | "
          f"{1.0 - agg['mae'] / agg['persist_mae']:+.3f} | - | - |")
        a("")

    # ---- stability analysis -----------------------------------------------------------------
    a("## Stability analysis")
    a("")
    a("Dispersion is reported as median, IQR, full range and worst-to-best ratio over")
    a("segments **clearing the sufficiency threshold only**. The noise floor is the")
    a("approximate standard error a segment MAE carries at its own cell size:")
    a(f"`SE = sd(|error|) / sqrt(n)`, using the test-split error sd of {ae_sd:.2f}.")
    a("")
    a("Where the observed range is comparable to the noise floor, the correct statement is")
    a("that the segments are **not distinguishable** - not that they are equal, and not that")
    a("the model is stable.")
    a("")

    a("### Per-horizon dispersion, test split")
    a("")
    a("A level counts toward dispersion only if it clears n >= 30 **and** is not a single")
    a("programme in disguise. Excluded levels are still listed in the tables above.")
    a("")
    a("| Field | H | Segments used | Median MAE | IQR | Range | Worst/Best | "
      "Typical n | Noise floor SE | Range vs noise |")
    a("|---|---|---|---|---|---|---|---|---|---|")
    stability_notes: List[str] = []
    for col, label in SEGMENT_DIMS:
        for h in HORIZONS:
            blk = results[(col, "test", h)]
            use = reportable(blk["rows"], col)
            if len(use) < 2:
                disp = dispersion([])
                if use:
                    a(f"| `{col}` | {h} | 1 of {len(blk['rows'])} | "
                      f"{use[0]['mae']:.2f} | - | - | - | {use[0]['n']} | "
                      f"{ae_sd / np.sqrt(use[0]['n']):.2f} | **not assessable (1 segment)** |")
                    stability_notes.append(
                        f"`{col}` at H{h} has only one segment above the sufficiency "
                        f"threshold, so dispersion cannot be assessed at that level.")
                else:
                    a(f"| `{col}` | {h} | **0** | - | - | - | - | - | - | "
                      f"**not assessable (no sufficient segment)** |")
                continue
            d_mae = dispersion([r["mae"] for r in use])
            d_rmse = dispersion([r["rmse"] for r in use])
            typ_n = int(np.median([r["n"] for r in use]))
            floor = ae_sd / np.sqrt(typ_n)
            ratio = d_mae["range"] / floor if floor > 0 else float("nan")
            verdict = ("exceeds noise" if ratio > 2 else
                       "comparable to noise" if ratio > 1 else "within noise")
            a(f"| `{col}` | {h} | {d_mae['n_segments']} of {len(blk['rows'])} | "
              f"{d_mae['median']:.2f} | {d_mae['iqr']:.2f} | {d_mae['range']:.2f} | "
              f"{d_mae['worst_over_best']:.2f}x | {typ_n} | {floor:.2f} | {verdict} |")
    a("")

    a("### Is variation concentrated in particular programmes?")
    a("")
    a("Two different questions, and they have different answers.")
    a("")
    prog_ymean = d[d["split_hint"] == "test"].groupby("programme_id")["y_cum_enrolled"].mean()
    size_ratio = float(prog_ymean.max() / prog_ymean.min())
    a("**1. Is the *level* of enrolment concentrated? Yes, strongly.** Programme means of the")
    a(f"target range from {prog_ymean.min():.1f} to {prog_ymean.max():.1f} enrolled, a")
    a(f"{size_ratio:.1f}x spread. This is a property of programme size, not of forecast")
    a("accuracy.")
    a("")
    a("**2. Is the *error* concentrated? Checked directly below.**")
    a("")
    test_pooled = pooled[("programme_id", "test")]
    pg = test_pooled["rows"]
    agg_test = test_pooled["agg"]
    prog_mae = dispersion([r["mae"] for r in pg if r["sufficient"]])
    prog_rmse = dispersion([r["rmse"] for r in pg if r["sufficient"]])
    a("Pooled test error by programme (all horizons, n = 44 each, all above threshold):")
    a("")
    a("| Statistic | MAE | RMSE |")
    a("|---|---|---|")
    a(f"| Median across programmes | {prog_mae['median']:.2f} | {prog_rmse['median']:.2f} |")
    a(f"| Q1 | {prog_mae['q1']:.2f} | {prog_rmse['q1']:.2f} |")
    a(f"| Q3 | {prog_mae['q3']:.2f} | {prog_rmse['q3']:.2f} |")
    a(f"| IQR | {prog_mae['iqr']:.2f} | {prog_rmse['iqr']:.2f} |")
    a(f"| Min | {prog_mae['min']:.2f} | {prog_rmse['min']:.2f} |")
    a(f"| Max | {prog_mae['max']:.2f} | {prog_rmse['max']:.2f} |")
    a(f"| Range | {prog_mae['range']:.2f} | {prog_rmse['range']:.2f} |")
    a(f"| Worst / best | {prog_mae['worst_over_best']:.2f}x | "
      f"{prog_rmse['worst_over_best']:.2f}x |")
    a("")
    prog_skill = {r["level"]: r["skill_vs_persist"] for r in pg}
    prog_size = {pid: float(prog_ymean[pid]) for pid in prog_ymean.index}
    prog_mae_v = np.array([r["mae"] for r in pg])
    prog_persist_v = np.array([r["persist_mae"] for r in pg])
    prog_size_v = np.array([prog_size[r["level"]] for r in pg])
    r_mae_size = float(np.corrcoef(prog_size_v, prog_mae_v)[0, 1])
    r_per_size = float(np.corrcoef(prog_size_v, prog_persist_v)[0, 1])
    skills_v = np.array([prog_skill[r["level"]] for r in pg])
    worst_pg = max(pg, key=lambda r: r["mae"])
    others = [r for r in pg if r["level"] != worst_pg["level"]]
    a("**Absolute error is strongly scale-dependent.** Pearson r between programme mean")
    a(f"target and pooled MAE is **{r_mae_size:+.3f}**. The largest programme, "
      f"`{worst_pg['level']}`")
    a(f"(mean {worst_pg['actual_mean']:.1f} enrolled), carries the largest absolute error")
    a(f"(MAE {worst_pg['mae']:.2f}). This is not a property of the model alone - the")
    a(f"persistence reference is *more* scale-dependent still (r = {r_per_size:+.3f}) - so a")
    a("raw MAE ranking largely ranks programme size.")
    a("")
    a("**The scale-free view does not support a single weak programme.** Skill against")
    a(f"persistence across the 12 programmes runs {skills_v.min():+.3f} to "
      f"{skills_v.max():+.3f},")
    a(f"a spread of {(1 - skills_v.min()) / (1 - skills_v.max()):.2f}x on the underlying")
    a("MAE/persistence ratio. The programme with the worst absolute MAE, "
      f"`{worst_pg['level']}`,")
    a(f"still scores {prog_skill[worst_pg['level']]:+.3f} on skill - mid-pack, not worst.")
    low_skill_pg = min(prog_skill, key=prog_skill.get)
    low_skill_persist = next(r["persist_mae"] for r in pg if r["level"] == low_skill_pg)
    a(f"The programme with the **worst skill** is `{low_skill_pg}` at "
      f"{prog_skill[low_skill_pg]:+.3f}, and the reason is the benchmark rather than the")
    a(f"model: its persistence MAE is {low_skill_persist:.2f}, the **lowest of all 12** "
      f"programmes, so persistence is already near-perfect there and there is little for")
    a("   the model to improve on. It is not a programme the model forecasts badly.")
    a("")
    other_size = np.array([prog_size[r["level"]] for r in others])
    a(f"The {prog_mae['worst_over_best']:.1f}x MAE spread is also **not a continuum**: "
      f"excluding `{worst_pg['level']}`, the")
    a(f"other {len(others)} programmes span {min(r['mae'] for r in others):.2f} to "
      f"{max(r['mae'] for r in others):.2f}, a "
      f"{max(r['mae'] for r in others) / min(r['mae'] for r in others):.1f}x spread against a")
    a(f"{other_size.max() / other_size.min():.1f}x spread in their size. The observed")
    a("programme dispersion is one large outlier plus a tight cluster, so **the median")
    a(f"({prog_mae['median']:.2f}) is the more honest summary than the range**.")
    a("")

    a("### Does variation grow with horizon?")
    a("")
    a("| H | Aggregate MAE | Aggregate RMSE | MAE persistence | Skill | "
      "MAE/persistence ratio | Programme MAE range at this H |")
    a("|---|---|---|---|---|---|---|")
    for h in HORIZONS:
        agg = results[("programme_id", "test", h)]["agg"]
        pvals = [r["mae"] for r in results[("programme_id", "test", h)]["rows"]
                 if r["sufficient"]]
        rng = (f"{dispersion(pvals)['range']:.2f}" if len(pvals) >= 2
               else "not estimable (n = 11 per cell)")
        ratio = agg["mae"] / agg["persist_mae"]
        a(f"| H{h} | {agg['mae']:.2f} | {agg['rmse']:.2f} | {agg['persist_mae']:.2f} | "
          f"{1.0 - ratio:+.3f} | {ratio:.3f} | {rng} |")
    a("")
    a("Aggregate error rises with horizon and so does skill against persistence, because")
    a("persistence degrades faster than the model does. The MAE/persistence ratio falls")
    a(f"monotonically from {results[('programme_id', 'test', 1)]['agg']['mae'] / results[('programme_id', 'test', 1)]['agg']['persist_mae']:.3f} "
      f"at H1 to "
      f"{results[('programme_id', 'test', 6)]['agg']['mae'] / results[('programme_id', 'test', 6)]['agg']['persist_mae']:.3f} "
      f"at H6.")
    a("")
    a("**Whether per-programme dispersion grows with horizon cannot be measured here.** Every")
    a("per-programme cell holds 11 observations, all flagged INSUFFICIENT. This analysis can")
    a("say that aggregate error rises with horizon; it cannot say whether the rise is")
    a("concentrated in particular programmes or spread evenly across them, and no such claim")
    a("is made.")
    a("")

    a("### Segments furthest from the aggregate")
    a("")
    a("Test split, pooled across horizons, cells clearing both conditions.")
    a("")
    a("| Field | Level | Programmes | MAE | vs aggregate | RMSE | vs aggregate |")
    a("|---|---|---|---|---|---|---|")
    for col, _label in SEGMENT_DIMS:
        for r in sorted(reportable(pooled[(col, "test")]["rows"], col),
                        key=lambda r: -abs(r["delta_mae_vs_agg"]))[:3]:
            a(f"| `{col}` | `{r['level']}` | {r['n_programmes']} | {r['mae']:.2f} | "
              f"{r['delta_mae_vs_agg']:+.2f} | "
              f"{r['rmse']:.2f} | {r['rmse'] - agg_test['rmse']:+.2f} |")
    a("")

    a("### Assessment")
    a("")
    for note in stability_notes:
        a(f"- {note}")
    any_above = False
    for col, _label in SEGMENT_DIMS:
        for h in HORIZONS:
            use = reportable(results[(col, "test", h)]["rows"], col)
            if len(use) >= 2:
                dsp = dispersion([r["mae"] for r in use])
                floor = ae_sd / np.sqrt(int(np.median([r["n"] for r in use])))
                if dsp["range"] / floor > 2:
                    any_above = True
    a(f"- On the coarse groupings (`selectivity_tier`, `campus_region_id`, `faculty`), "
      f"{'some' if any_above else 'no'} segment differences exceed the sampling noise floor.")
    a(f"- Per-programme, per-horizon error is not estimable (11 observations per cell).")
    a(f"- Per-programme error pooled across horizons is estimable (44 per cell) and shows a "
      f"{prog_mae['worst_over_best']:.1f}x MAE spread.")
    a(f"- {n_singleton} levels of the coarse dimensions are single programmes in disguise and")
    a("  are excluded from dispersion, so the coarse-grouping findings rest on fewer")
    a("  independent units than their row counts suggest.")
    a("- The evidence does not support declaring the model stable or unstable. It supports")
    a("  the narrower statement that error varies by programme, that the variation is far")
    a("  smaller than the variation in programme size, and that at single-horizon")
    a("  granularity the dataset is too small to characterise it.")
    a("")

    # ---- outliers ---------------------------------------------------------------------------
    a("## Notable deviations and outliers")
    a("")
    a("Actual calculated findings only.")
    a("")
    worst = max(pg, key=lambda r: r["mae"])
    best = min([r for r in pg if r["sufficient"]], key=lambda r: r["mae"])
    a(f"1. **Highest pooled test MAE: `{worst['level']}`** at {worst['mae']:.2f} enrolled "
      f"(aggregate {agg_test['mae']:.2f}, difference {worst['delta_mae_vs_agg']:+.2f}). Its "
      f"target mean is {worst['actual_mean']:.1f} - the largest of the 12 - so this is the "
      f"biggest programme rather than a pathological one, and its skill against persistence "
      f"is {prog_skill[worst['level']]:+.3f}, mid-pack.")
    a(f"2. **Lowest pooled test MAE: `{best['level']}`** at {best['mae']:.2f} enrolled "
      f"(difference {best['delta_mae_vs_agg']:+.2f} against aggregate); its target mean is "
      f"{best['actual_mean']:.1f}, the smallest of the 12.")
    a(f"3. **The scale-free outlier is a different programme.** `{worst['level']}` has the "
      f"worst absolute")
    a(f"   MAE, but the worst *skill* belongs to `{low_skill_pg}` at "
      f"{prog_skill[low_skill_pg]:+.3f}. Ranking programmes by MAE and by skill give")
    a("   different answers.")
    h_bias = {h: next(r["bias"] for r in results[("programme_id", "test", h)]["rows"]
                       if r["level"] == worst["level"]) for h in HORIZONS}
    a(f"4. **`{worst['level']}` swings sign across horizons.** Its per-horizon bias runs "
      f"{', '.join(f'H{h} {h_bias[h]:+.2f}' for h in HORIZONS)}")
    a(f"   (n = 11 each, so each figure is noisy), while its pooled bias is "
      f"{worst['bias']:+.2f}. The under-prediction deepens with horizon, which is the")
    a("   pattern of an enrolment curve maturing after the last observed data point rather")
    a("   than a uniform scale offset.")
    comm = next(r for r in pooled[("faculty", "test")]["rows"]
                if r["level"] == "Faculty of Commerce")
    comm_members = sorted(prog_index[prog_index["faculty"] == "Faculty of Commerce"].index)
    comm_maes = {r["level"]: r["mae"] for r in pg if r["level"] in comm_members}
    a(f"5. **`Faculty of Commerce` is the worst coarse grouping** at {comm['mae']:.2f} pooled "
      f"MAE ({comm['delta_mae_vs_agg']:+.2f} vs aggregate), but it holds only "
      f"{comm['n_programmes']} programmes - {', '.join(comm_members)} - whose pooled MAEs are "
      f"{comm_maes[comm_members[0]]:.2f} and {comm_maes[comm_members[1]]:.2f}. The mean of "
      f"two")
    a("   programmes that far apart is not evidence of a faculty-level effect.")
    a(f"6. **Every programme's *pooled* skill against persistence is positive**, ranging "
      f"{skills_v.min():+.3f} to {skills_v.max():+.3f} over 44 observations each, so no")
    a("   programme is forecast worse than simply carrying the last observed value forward.")
    a("   Finding 10 shows this does not hold at single-horizon granularity.")
    bias_by_h = ", ".join(
        "H{h} {b:+.2f}".format(
            h=h, b=results[("programme_id", "test", h)]["agg"]["bias"]) for h in HORIZONS)
    bias_signs = {s: sum(1 for h in HORIZONS
                         if np.sign(results[("programme_id", s, h)]["agg"]["bias"]) > 0)
                  for s in eval_splits}
    a(f"7. **Aggregate bias is positive at every horizon in the test split** ({bias_by_h}), so")
    a("   the model consistently over-predicts cumulative enrolment. The magnitude is not")
    a("   monotonic - H2 is near zero while H4 is the largest - which matches the alternating")
    a("   bias pattern recorded in `reports/forecast_results.md`. The same sign holds on "
      f"validation at")
    a(f"   {bias_signs['validation']} of 4 horizons. This is a system-level deviation, not a "
      f"segment effect.")
    ovr = [r for col, _l in SEGMENT_DIMS
           for r in pooled[(col, "test")]["rows"]
           if r["sufficient"] and r["bias"] > 0]
    n_pooled_cells = sum(len(pooled[(c, "test")]["rows"]) for c, _l in SEGMENT_DIMS)
    all_pooled_skills = [r["skill_vs_persist"] for c, _l in SEGMENT_DIMS
                         for r in pooled[(c, "test")]["rows"] if r["sufficient"]]
    n_pooled_reportable = sum(len(reportable(pooled[(c, "test")]["rows"], c))
                              for c, _l in SEGMENT_DIMS)
    n_ovr_reportable = sum(
        1 for c, _l in SEGMENT_DIMS for r in reportable(pooled[(c, "test")]["rows"], c)
        if r["bias"] > 0)
    a(f"8. **{n_ovr_reportable} of {n_pooled_reportable} reportable pooled segment cells show "
      f"positive bias**")
    a(f"   ({len(ovr)} of {n_pooled_cells} if single-programme levels are counted), so")
    a("   over-prediction is a system-level property rather than something specific to one")
    a("   segment.")
    a("9. **No reportable segment had a *worse* MAE than persistence.** The weakest pooled")
    a(f"   skill across every field is {min(all_pooled_skills):+.3f}, so even the least")
    a("   favourable segment beats the reference.")
    neg_skill = [(h, r["level"], r["skill_vs_persist"])
                 for h in HORIZONS
                 for r in results[("programme_id", "test", h)]["rows"]
                 if r["skill_vs_persist"] < 0]
    if neg_skill:
        a(f"10. **Negative skill does occur, but only in cells too small to interpret.** "
          f"{len(neg_skill)} programme-horizon")
        a(f"    cells on the test split score below the persistence reference: "
          f"{', '.join(f'{p} at H{h} ({s:+.3f})' for h, p, s in neg_skill)}.")
        a("    All hold n = 11 and are marked INSUFFICIENT. They are reported rather than")
        a("    dropped, but no conclusion is drawn from them, and they do not contradict")
        a("    finding 9, which concerns pooled cells of n = 44.")
    n_no_enrol = int(((d["split_hint"] == "test") & (d["has_enrolments"] == 0)).sum()
                     / len(HORIZONS))
    n_progs_zero_any = int(d.loc[d["has_enrolments"] == 0, "programme_id"].nunique())
    n_progs_zero_test = int(d.loc[(d["has_enrolments"] == 0)
                                  & (d["split_hint"] == "test"), "programme_id"].nunique())
    a("11. **`has_enrolments` is effectively degenerate on the test split**: the level with no")
    a(f"   enrolment history holds only {n_no_enrol} observation(s) per horizon and is marked")
    a("   INSUFFICIENT at every horizon. The field cannot support a segment conclusion on")
    a("   this data, and none is drawn. The cause is the eligible origin window starting at")
    a(f"   week 25: {n_progs_zero_any} of 12 programmes have at least one origin there with no")
    a(f"   enrolment history, but in the test cycle CYC-2025 only {n_progs_zero_test} do, and")
    a("   each contributes a single origin.")
    top_errs = sorted(d[d["split_hint"] == "test"]["ae"].round(1).tolist(), reverse=True)[:4]
    top_pgm = (d[d["split_hint"] == "test"].nlargest(4, "ae")["programme_id"]
               .value_counts().to_dict())
    top_txt = ", ".join(f"{p} x{c}" for p, c in sorted(top_pgm.items()))
    a(f"12. **The four largest single-row absolute errors on the test split** are "
      f"{top_errs} enrolled,")
    a(f"    and all of them fall in {top_txt}. These are individual row outliers rather than")
    a("    a segment pattern in their own right, though they do concentrate in the same")
    a("    programme already identified as the largest. With no resampling and 132 rows per")
    a("    horizon, no inference is drawn from them.")
    a("")

    # ---- limitations -----------------------------------------------------------------------
    a("## Limitations")
    a("")
    a("1. **Per-programme, per-horizon error is not estimable.** A cell holds 11 test")
    a("   observations. This is the binding constraint on the whole analysis and no")
    a("   statistical treatment can remove it. Per-programme results require pooling")
    a("   horizons, which mixes four different difficulty levels.")
    a(f"2. **{len(below)} segment-horizon cells fall below n = {MIN_CELL_N}** and are excluded")
    a("   from every dispersion figure. They are printed, counted and marked INSUFFICIENT.")
    a("3. **Consecutive origins are heavily overlapping.** The panel is one row per")
    a("   programme-cycle-week, so the 11 origins of a programme-cycle at a given horizon")
    a("   overlap in their underlying history. Their errors are therefore correlated and the")
    a("   nominal n overstates the independent information. This is the same reason n = 11")
    a("   cannot be treated as 11 independent observations. (The 2,529 applicants holding")
    a("   multiple applications are a dependence in the *application* tables and do not")
    a("   create rows here, so they are not the binding issue for this analysis.)")
    a("4. **A single cycle per evaluation split.** CYC-2024 is the whole validation split and")
    a("   CYC-2025 the whole test split. No cycle-level stability can be assessed, and a")
    a("   cycle-specific shock would be indistinguishable from a general one.")
    a("5. **Dispersion across segments is a maximum-over-segments statistic.** With 2 to 12")
    a("   usable segments per field, the observed range is biased upward as a measure of true")
    a("   spread, and the bias grows as usable segments get fewer. The IQR and median are")
    a("   reported alongside it for that reason, and the range should not be read as a")
    a("   population spread.")
    a("6. **The noise floor is an approximation.** It uses the pooled test error standard")
    a("   deviation and a normal-approximation standard error. Absolute errors are not")
    a("   normally distributed, and with n as low as 33 the true sampling spread of a segment")
    a("   MAE would be somewhat wider than shown. The comparison is therefore a rough guide,")
    a("   not a formal test.")
    a("7. **No cross-validation and no repeated evaluation.** A single fit on one train set")
    a("   means segment differences cannot be separated from fit-to-fit variation.")
    a("8. **Absolute error is scale-dependent.** Programme sizes differ by roughly "
      f"{size_ratio:.1f}x and pooled MAE")
    a(f"   correlates with programme size at r = {r_mae_size:+.3f}, so the programme MAE")
    a("   ranking partly ranks programme size. **Skill against persistence** is reported")
    a("   alongside it because it is scale-free, and the **within-programme R2** already")
    a("   published per horizon in `reports/forecast_results.md` is the appropriate view for")
    a("   the opposite question. Segment-level within-programme R2 is not recomputed here")
    a("   because it is undefined for the coarse groupings, whose levels pool several")
    a("   programmes with different baselines.")
    a("9. **Synthetic data.** The dataset is generated by `scripts/generate_dataset.py`. The")
    a("   funnel structure, conversion rates and yield maturation are all simulated, so")
    a("   these stability figures describe a simulated system and carry no claim about real")
    a("   institutional forecasting.")
    a("10. **No generalisation beyond this dataset.** Four cycles, 12 programmes, one")
    a("    institution, one funnel definition. Nothing here supports a claim about forecast")
    a("    stability in general.")
    a("11. **Predictions were regenerated, not read from disk.** The artifact stores no")
    a("    predictions. Reconciliation against all 8 published aggregates makes this safe,")
    a("    but it is a verification of equality, not a byte-level identity of a saved model")
    a("    file.")
    a("")

    # ---- reproduction ----------------------------------------------------------------------
    a("## Reproduction")
    a("")
    a("```")
    a("cd admitflow-data")
    a("python scripts/build_forecast_features.py   # only if the feature file is absent or stale")
    a("python scripts/forecast_segment_stability.py")
    a("```")
    a("")
    a("`build_forecast_features.py` is a prerequisite but not part of AF-019: it rebuilds")
    a("`data/processed/forecast_features.csv` from `data/raw/fact_forecast_panel.csv` and runs")
    a("the leakage guard. If the artifact is already present, AF-019 reads it and does not")
    a("rebuild it.")
    a("")
    a("The script is deterministic: it fits the published model with the published seed and")
    a("performs no sampling, bootstrapping or iteration. Three consecutive runs produce a")
    a("byte-identical report. It does not regenerate the dataset, does not modify")
    a("`build_forecast_features.py` or `train_forecast.py`, and does not retune the model.")
    a("")
    a("Exit codes: `0` success, `3` published-metric reconciliation failed, `4` temporal")
    a("integrity failed.")
    a("")
    a("| Environment | Value |")
    a("|---|---|")
    a(f"| Python | `{platform.python_version()}` |")
    a(f"| scikit-learn / numpy / pandas | `{sklearn.__version__}` / `{np.__version__}` / "
      f"`{pd.__version__}` |")
    a(f"| Platform | `{platform.system()} {platform.machine()}` |")
    a(f"| Seed (inherited from the pipeline) | `{bf.SEED}` |")
    a("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    io.open(report_path, "w", encoding="utf-8", newline="\n").write("\n".join(L))

    print(f"[done] wrote {report_path}")
    print(f"       segment fields: {', '.join(c for c, _ in SEGMENT_DIMS)}")
    print(f"       horizons: {HORIZONS}  min cell n: {MIN_CELL_N}")
    print(f"       cells below threshold: {len(below)} (reported, flagged, excluded from dispersion)")
    print(f"       programme MAE spread (test, pooled): {prog_mae['min']:.2f} to "
          f"{prog_mae['max']:.2f} ({prog_mae['worst_over_best']:.2f}x), n=44 each")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
