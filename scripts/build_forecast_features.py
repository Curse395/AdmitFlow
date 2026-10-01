#!/usr/bin/env python
"""
AdmitFlow - ROLLING-ORIGIN FORECAST FEATURE BUILDER
===================================================

Task   : build the supervised forecasting dataset for `cum_enrolled` at T + H
Grain  : one row per (programme_id, cycle_id, forecast origin T, horizon H)
Panel  : data/raw/fact_forecast_panel.csv   (programme x cycle x ISO week, 2,064 rows)
Origin : rows where `is_forecast_eligible = 1`, per contract F conditions 1-4
Horizon: H in {1, 2, 4, 6}
Split  : the panel's own `split_hint` (cycles 1-2 train, cycle 3 validation, cycle 4 test).
         No new split is invented. See contract E.5.

CONTRACT COMPLIANCE
-------------------
Contract E.3: "Forecasting features are the panel history strictly up to and including week T
plus the programme/cycle dimension attributes. Any panel value for week > T is post-origin
information and is excluded by construction (a rolling-origin feature builder must slice,
never look ahead)."

Every feature here is produced by `origin_features()`, which receives a frame already sliced
to `week_index_in_cycle <= T`. The builder never receives the post-origin rows in a usable
form. `n_applications` is deliberately EXCLUDED: it is a cycle total (verified constant
within every programme-cycle), so it is only knowable at cycle end and would be look-ahead.

THE LEAKAGE GUARD
-----------------
`run_leakage_guard()` is mandatory and executable. It proves no-look-ahead EMPIRICALLY rather
than by assertion, using a future-corruption invariance test:

  for every origin T, rebuild that origin's features from a panel in which EVERY panel value
  in weeks > T has been replaced with an extreme sentinel. If any feature derived from a
  future week, the rebuilt value would differ. All 552 origins are checked; none is sampled.

It also enforces an explicit column allow-list and verifies each target is the real observed
`cum_enrolled` at week T + H.

Run:
    python scripts/build_forecast_features.py                  # build + guard + write
    python scripts/build_forecast_features.py --verify-only    # guard only, no write
Exit code 4 means a look-ahead was detected.

The dataset is read-only. Nothing under data/raw is written or modified.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

SEED = 20240817

HORIZONS = [1, 2, 4, 6]

# Panel columns read as a time series. These are the only panel fields any feature may touch.
CUM_LEVELS = [
    "cum_applications_opened", "cum_applications_started", "cum_applications_submitted",
    "cum_applications_verified", "cum_decisions_issued", "cum_admitted", "cum_enrolled",
]
WK_FLOWS = [
    "wk_applications_submitted", "wk_applications_verified", "wk_decisions_issued",
    "wk_admitted", "wk_enrolled",
]
PANEL_RATES = ["cum_submit_to_verify_rate", "cum_admit_rate", "cum_enrolment_yield"]

# Explicitly NOT a feature. Cycle total, known only at cycle end.
EXCLUDED_PANEL_COLUMNS = {
    "n_applications": "cycle total; verified constant within every programme-cycle, so it is "
                      "post-origin information",
    "is_forecast_eligible": "origin-selection flag, not a quantity",
    "panel_id": "row key",
}

# Sentinel written into every post-origin panel value during the guard.
SENTINEL = 987_654_321.0

# Programme / cycle dimension attributes, all static and knowable at any origin.
DIM_PROGRAMME_NUM = ["duration_years", "annual_fee_inr", "base_seat_capacity",
                     "review_duration_days", "demand_weight"]
DIM_PROGRAMME_CAT = ["selectivity_tier", "campus_region_id", "award_level", "faculty"]
DIM_CYCLE_NUM = ["total_weeks", "cycle_year_offset"]

# `programme_id` is a legitimate static categorical: a programme is known at the origin and
# carries programme-level level differences across 12 programmes.
MODEL_CATEGORICAL = DIM_PROGRAMME_CAT + ["programme_id"]

# Carried on every row for traceability and grouping, but NEVER model inputs.
# `cycle_id` is the same class of field as `split_hint` in the classification task: the
# chronological holdout means every test cycle is an unseen level at training time, so it
# carries no usable signal and would only invite confusion with the split.
BOOKKEEPING = ["cycle_id", "split_hint", "origin_week_start_date", "origin_week_index",
               "target_week_index"]


class LookAheadError(RuntimeError):
    """Raised when a forecast feature is found to depend on panel data after the origin."""


# --------------------------------------------------------------------------------------
# Feature construction -- operates ONLY on a history slice ending at the origin
# --------------------------------------------------------------------------------------


def origin_features(hist: pd.DataFrame, origin_week: int) -> Dict[str, float]:
    """Numeric features for one origin, computed from `hist` alone.

    `hist` MUST already be sliced to week_index_in_cycle <= origin_week. This function has no
    access to any later row. Rolling windows are trailing windows ending at the origin.
    """
    h = hist.sort_values("week_index_in_cycle")
    n = len(h)
    last = h.iloc[-1]

    f: Dict[str, float] = {}

    # --- level of the funnel at the origin ---------------------------------------------
    for c in CUM_LEVELS:
        f[c] = float(last[c])
    for c in WK_FLOWS:
        f[f"{c}_at_origin"] = float(last[c])
    for c in PANEL_RATES:
        f[c] = float(last[c]) if pd.notna(last[c]) else np.nan

    f["week_index_in_cycle"] = float(origin_week)
    f["weeks_elapsed_in_cycle"] = float(n)

    # --- lags of the enrolment series (all are weeks <= T by construction) -------------
    by_week = h.set_index("week_index_in_cycle")
    for lag in (1, 2, 4):
        w = origin_week - lag
        f[f"lag_cum_enrolled_{lag}"] = (float(by_week.at[w, "cum_enrolled"])
                                       if w in by_week.index else np.nan)
    for lag in (1, 2, 3, 4):
        w = origin_week - lag
        f[f"lag_wk_enrolled_{lag}"] = (float(by_week.at[w, "wk_enrolled"])
                                       if w in by_week.index else np.nan)

    # --- trailing rolling statistics, windows ending at the origin ---------------------
    def roll_mean(col: str, k: int) -> float:
        return float(h[col].iloc[-k:].mean()) if n >= k else np.nan

    def roll_std(col: str, k: int) -> float:
        seg = h[col].iloc[-k:]
        return float(seg.std(ddof=0)) if n >= k and seg.notna().sum() > 1 else np.nan

    for k in (4, 8, 12):
        f[f"roll{k}_wk_enrolled_mean"] = roll_mean("wk_enrolled", k)
    for k in (4, 8):
        f[f"roll{k}_wk_enrolled_std"] = roll_std("wk_enrolled", k)
    for k in (4, 8):
        f[f"roll{k}_wk_submitted_mean"] = roll_mean("wk_applications_submitted", k)
    f["roll4_wk_decisions_mean"] = roll_mean("wk_decisions_issued", 4)
    f["roll4_wk_admitted_mean"] = roll_mean("wk_admitted", 4)

    # --- momentum -----------------------------------------------------------------------
    f["enrol_delta_4"] = (f["cum_enrolled"] - f["lag_cum_enrolled_4"]
                          if not np.isnan(f["lag_cum_enrolled_4"]) else np.nan)
    f["enrol_delta_1"] = (f["cum_enrolled"] - f["lag_cum_enrolled_1"]
                          if not np.isnan(f["lag_cum_enrolled_1"]) else np.nan)
    m4, m8 = f["roll4_wk_enrolled_mean"], f["roll8_wk_enrolled_mean"]
    f["enrol_acceleration"] = (m4 - m8) if not (np.isnan(m4) or np.isnan(m8)) else np.nan

    # --- how far the funnel has progressed in time --------------------------------------
    dec = h[h["cum_decisions_issued"] > 0]
    enr = h[h["cum_enrolled"] > 0]
    f["weeks_since_first_decision"] = (float(origin_week - dec["week_index_in_cycle"].min())
                                       if len(dec) else np.nan)
    f["weeks_since_first_enrolment"] = (float(origin_week - enr["week_index_in_cycle"].min())
                                        if len(enr) else np.nan)
    f["has_decisions"] = float(len(dec) > 0)
    f["has_enrolments"] = float(len(enr) > 0)

    return f


def build_group(group: pd.DataFrame, origin_weeks: Sequence[int],
                corrupt_after: Optional[int] = None) -> List[Dict]:
    """Build every (origin, horizon) row for one programme-cycle.

    `corrupt_after` is the guard's lever: when set, every panel value in weeks strictly
    greater than it is overwritten with SENTINEL before anything is computed, so any
    dependence on the future becomes visible as a changed feature value.
    """
    g = group.copy()
    if corrupt_after is not None:
        future = g["week_index_in_cycle"] > corrupt_after
        if future.any():
            g.loc[future, CUM_LEVELS + WK_FLOWS] = SENTINEL
            g.loc[future, PANEL_RATES] = SENTINEL
    g = g.sort_values("week_index_in_cycle").reset_index(drop=True)

    prog = g.iloc[0]
    rows: List[Dict] = []
    for t in origin_weeks:
        hist = g[g["week_index_in_cycle"] <= t]
        if hist.empty:
            continue
        base = origin_features(hist, t)
        for c in DIM_PROGRAMME_NUM:
            base[c] = float(prog[c]) if pd.notna(prog[c]) else np.nan
        for c in DIM_CYCLE_NUM:
            base[c] = float(prog[c]) if pd.notna(prog[c]) else np.nan
        for c in DIM_PROGRAMME_CAT:
            base[c] = prog[c]
        base["programme_id"] = prog["programme_id"]
        base["cycle_id"] = prog["cycle_id"]
        base["split_hint"] = prog["split_hint"]
        base["origin_week_index"] = int(t)
        base["origin_week_start_date"] = str(
            g.loc[g["week_index_in_cycle"] == t, "week_start_date"].iloc[0])

        for h in HORIZONS:
            target_week = t + h
            hit = g[g["week_index_in_cycle"] == target_week]
            if hit.empty:
                continue
            row = dict(base)
            row["horizon_weeks"] = int(h)
            row["target_week_index"] = int(target_week)
            row["y_cum_enrolled"] = float(hit["cum_enrolled"].iloc[0])
            rows.append(row)
    return rows


# --------------------------------------------------------------------------------------
# Leakage guard
# --------------------------------------------------------------------------------------


def numeric_feature_names() -> List[str]:
    probe = pd.DataFrame([{c: 0.0 for c in CUM_LEVELS + WK_FLOWS + PANEL_RATES}])
    names = list(origin_features(probe.assign(week_index_in_cycle=range(len(probe))), 0))
    return names + DIM_PROGRAMME_NUM + DIM_CYCLE_NUM + ["horizon_weeks"]


def run_leakage_guard(panel: pd.DataFrame, built: pd.DataFrame,
                      feature_cols: Sequence[str]) -> Dict[str, int]:
    """Prove, executably, that no feature depends on panel data after its origin.

    Returns a dict of check counts. Raises LookAheadError on the first violation so the
    training script fails closed rather than training on contaminated features.
    """
    checks = {"origins_tested": 0, "feature_cells_compared": 0, "targets_verified": 0}

    # ---- check 1: explicit allow-list -------------------------------------------------
    forbidden = set(EXCLUDED_PANEL_COLUMNS)
    illegal = [c for c in feature_cols
               if c in forbidden or c.startswith("cum_") and c in ("cum_enrolled_future",)]
    leaked = [c for c in feature_cols if c in forbidden]
    if leaked:
        raise LookAheadError(f"excluded/post-origin columns in the feature matrix: {leaked}")
    if illegal:
        raise LookAheadError(f"illegal feature columns: {illegal}")

    # ---- check 2: target integrity -----------------------------------------------------
    # Every target must be the genuinely observed cum_enrolled at week origin + H.
    key = ["programme_id", "cycle_id"]
    lut = {(r.programme_id, r.cycle_id, r.week_index_in_cycle): r.cum_enrolled
           for r in panel.itertuples()}
    for r in built.itertuples():
        want = lut.get((r.programme_id, r.cycle_id, r.target_week_index))
        if want is None:
            raise LookAheadError(
                f"target week {r.target_week_index} is not a real observed panel cell for "
                f"{r.programme_id}/{r.cycle_id}")
        if abs(float(want) - float(r.y_cum_enrolled)) > 1e-9:
            raise LookAheadError(
                f"target mismatch at {r.programme_id}/{r.cycle_id} origin "
                f"{r.origin_week_index} H={r.horizon_weeks}")
        if r.target_week_index != r.origin_week_index + r.horizon_weeks:
            raise LookAheadError("target week is not origin + H")
        checks["targets_verified"] += 1

    # ---- check 3: future-corruption invariance (the real proof) -------------------------
    # For every origin, rebuild from a panel whose future is overwritten with an extreme
    # sentinel. A feature that touched a future week would change value.
    clean_by_origin: Dict[Tuple[str, str, int, int], Dict] = {}
    for r in built.itertuples():
        clean_by_origin[(r.programme_id, r.cycle_id, r.origin_week_index,
                         r.horizon_weeks)] = r._asdict()

    merged = panel.merge(
        _dim_programme(), on="programme_id", how="left").merge(
        _dim_cycle(), on="cycle_id", how="left")

    numeric_only = [c for c in feature_cols if c not in MODEL_CATEGORICAL]
    for (pid, cid), grp in merged.groupby(["programme_id", "cycle_id"]):
        origins = sorted(built.loc[(built["programme_id"] == pid) &
                                   (built["cycle_id"] == cid),
                                   "origin_week_index"].unique())
        for t in origins:
            rebuilt = build_group(grp, [t], corrupt_after=t)
            for row in rebuilt:
                k = (pid, cid, row["origin_week_index"], row["horizon_weeks"])
                ref = clean_by_origin.get(k)
                if ref is None:
                    continue
                for c in numeric_only:
                    a, b = ref.get(c), row.get(c)
                    same = (pd.isna(a) and pd.isna(b)) or (
                        a is not None and b is not None and abs(float(a) - float(b)) < 1e-9)
                    checks["feature_cells_compared"] += 1
                    if not same:
                        raise LookAheadError(
                            f"feature '{c}' for {pid}/{cid} origin {t} H="
                            f"{row['horizon_weeks']} changed when post-origin panel values were "
                            f"corrupted: {a!r} -> {b!r}. It is derived from a week after the "
                            f"forecast origin.")
                for c in MODEL_CATEGORICAL:
                    if ref.get(c) != row.get(c):
                        raise LookAheadError(f"categorical attribute '{c}' is not stable")
            checks["origins_tested"] += 1

    return checks


# --------------------------------------------------------------------------------------
# Dimension lookups
# --------------------------------------------------------------------------------------


_DIM_CACHE: Dict[str, pd.DataFrame] = {}


def _dim_programme() -> pd.DataFrame:
    if "prog" not in _DIM_CACHE:
        p = pd.read_csv(ROOT / "data" / "raw" / "dim_programme.csv")
        _DIM_CACHE["prog"] = p
    return _DIM_CACHE["prog"]


def _dim_cycle() -> pd.DataFrame:
    if "cyc" not in _DIM_CACHE:
        c = pd.read_csv(ROOT / "data" / "raw" / "dim_admission_cycle.csv")
        c["cycle_start_date"] = pd.to_datetime(c["cycle_start_date"])
        c["cycle_year_offset"] = c["cycle_start_date"].dt.year - 2022
        c = c.drop(columns=["cycle_start_date"])
        _DIM_CACHE["cyc"] = c
    return _DIM_CACHE["cyc"]


def load_panel(root: Path) -> pd.DataFrame:
    p = pd.read_csv(root / "data" / "raw" / "fact_forecast_panel.csv")
    p["week_start_date"] = pd.to_datetime(p["week_start_date"])
    return p


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------


def self_test(panel: pd.DataFrame, feature_cols: Sequence[str]) -> bool:
    """Prove the guard can actually FAIL, by injecting a deliberate look-ahead.

    A guard that has never been seen to reject anything is not evidence of safety. This
    simulates the exact bug the guard exists to catch - a builder that forgets to slice the
    history and therefore reads weeks after the origin - and asserts the guard rejects it.

    Returns True if the guard correctly detected the injected leak.
    """
    import types

    global build_group
    real_build_group = build_group

    def leaky_build_group(group, origin_weeks, corrupt_after=None):
        g = group.copy()
        if corrupt_after is not None:          # same corruption the guard applies
            fut = g["week_index_in_cycle"] > corrupt_after
            if fut.any():
                g.loc[fut, CUM_LEVELS + WK_FLOWS] = SENTINEL
                g.loc[fut, PANEL_RATES] = SENTINEL
        g = g.sort_values("week_index_in_cycle").reset_index(drop=True)
        prog = g.iloc[0]
        rows = []
        for t in origin_weeks:
            hist = g                             # <-- THE BUG: not sliced to <= t
            base = origin_features(hist, t)
            for c in DIM_PROGRAMME_NUM:
                base[c] = float(prog[c]) if pd.notna(prog[c]) else np.nan
            for c in DIM_CYCLE_NUM:
                base[c] = float(prog[c]) if pd.notna(prog[c]) else np.nan
            for c in DIM_PROGRAMME_CAT:
                base[c] = prog[c]
            base["programme_id"] = prog["programme_id"]
            base["cycle_id"] = prog["cycle_id"]
            base["split_hint"] = prog["split_hint"]
            base["origin_week_index"] = int(t)
            base["origin_week_start_date"] = str(
                g.loc[g["week_index_in_cycle"] == t, "week_start_date"].iloc[0])
            # the leaked column: the final cum_enrolled in the whole cycle
            base["LEAK_full_cycle_cum_enrolled"] = float(g["cum_enrolled"].max())
            for h in HORIZONS:
                hit = g[g["week_index_in_cycle"] == t + h]
                if hit.empty:
                    continue
                row = dict(base)
                row["horizon_weeks"] = int(h)
                row["target_week_index"] = int(t + h)
                row["y_cum_enrolled"] = float(hit["cum_enrolled"].iloc[0])
                rows.append(row)
        return rows

    merged = (panel.merge(_dim_programme(), on="programme_id", how="left")
                    .merge(_dim_cycle(), on="cycle_id", how="left"))
    rows: List[Dict] = []
    build_group = leaky_build_group
    try:
        for (_pid, _cid), grp in merged.groupby(["programme_id", "cycle_id"]):
            origins = sorted(grp.loc[grp["is_forecast_eligible"],
                                     "week_index_in_cycle"].tolist())
            rows.extend(leaky_build_group(grp, origins))
        leaky = pd.DataFrame(rows)
        cols = list(feature_cols) + ["LEAK_full_cycle_cum_enrolled"]
        try:
            run_leakage_guard(panel, leaky, cols)
        except LookAheadError as exc:
            print(f"[self-test] PASS  guard rejected the injected look-ahead: "
                  f"{str(exc)[:150]}...")
            return True
        print("[self-test] FAIL  guard did NOT reject an injected look-ahead feature")
        return False
    finally:
        build_group = real_build_group


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build rolling-origin forecast features")
    ap.add_argument("--root", default=str(ROOT), help="dataset root")
    ap.add_argument("--out", default=None, help="output CSV path")
    ap.add_argument("--verify-only", action="store_true",
                    help="run the leakage guard without writing the feature file")
    ap.add_argument("--fail-on-lookahead", action="store_true",
                    help="exit non-zero if the guard detects any look-ahead (it always does)")
    ap.add_argument("--self-test", action="store_true",
                    help="inject a deliberate look-ahead and assert the guard rejects it")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    out = Path(args.out) if args.out else root / "data" / "processed" / "forecast_features.csv"
    np.random.seed(SEED)

    panel = load_panel(root)
    merged = (panel.merge(_dim_programme(), on="programme_id", how="left")
                    .merge(_dim_cycle(), on="cycle_id", how="left"))

    rows: List[Dict] = []
    for (_pid, _cid), grp in merged.groupby(["programme_id", "cycle_id"]):
        origins = sorted(grp.loc[grp["is_forecast_eligible"], "week_index_in_cycle"].tolist())
        rows.extend(build_group(grp, origins))

    built = pd.DataFrame(rows)
    feature_cols = [c for c in dict.fromkeys(
        numeric_feature_names() + MODEL_CATEGORICAL) if c in built.columns]

    if args.self_test:
        print("[self-test] injecting a deliberate look-ahead to prove the guard can fail...")
        return 0 if self_test(panel, feature_cols) else 5

    print(f"[build] {len(built):,} feature rows from "
          f"{built.groupby(['programme_id', 'cycle_id', 'origin_week_index']).ngroups:,} "
          f"origins x {len(HORIZONS)} horizons")
    print(f"[build] {len(feature_cols)} feature columns "
          f"({len(numeric_feature_names())} numeric, {len(DIM_PROGRAMME_CAT)} categorical)")

    # ---- MANDATORY leakage guard --------------------------------------------------------
    try:
        checks = run_leakage_guard(panel, built, feature_cols)
    except LookAheadError as exc:
        print("LEAKAGE GUARD FAILED")
        print("   ", exc)
        return 4
    print(f"[guard] PASS  origins_tested={checks['origins_tested']} "
          f"feature_cells_compared={checks['feature_cells_compared']:,} "
          f"targets_verified={checks['targets_verified']:,}")
    print(f"[guard] PASS  future-corruption invariance: rebuilding every origin from a panel "
          f"with all weeks > T overwritten by {int(SENTINEL)} reproduced identical features")
    print(f"[guard] PASS  excluded as post-origin: "
          f"{', '.join(sorted(EXCLUDED_PANEL_COLUMNS))}")

    if args.verify_only:
        print("[done] --verify-only: guard passed, nothing written")
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    ordered = (["programme_id", "cycle_id", "split_hint", "origin_week_start_date",
                "origin_week_index", "target_week_index", "horizon_weeks", "y_cum_enrolled"]
               + feature_cols)
    ordered = [c for c in dict.fromkeys(ordered) if c in built.columns]
    built[ordered].to_csv(out, index=False, float_format="%.6f")
    print(f"[done] wrote {out}  ({len(built):,} rows x {len(ordered)} cols)")

    print("[rows by split x horizon]")
    for s in ("train", "validation", "test"):
        for h in HORIZONS:
            m = (built["split_hint"] == s) & (built["horizon_weeks"] == h)
            print(f"   {s:11s} H={h}  n={int(m.sum()):5d}  "
                  f"mean_y={built.loc[m, 'y_cum_enrolled'].mean():8.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
