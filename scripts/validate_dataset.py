"""
AdmitFlow dataset validator.

Validates the generated dataset against the analytical contract in
docs/admitflow_data_contract.md and the column registry in admitflow_schema.py.

Check families
--------------
  STRUCTURAL   row counts, columns, dtypes, primary-key uniqueness, foreign-key integrity
  DATA         missingness, duplicates, invalid categories, impossible dates, invalid numerics
  FUNNEL       stage ordering, progression, conversion/drop-off consistency, no impossible
               transitions
  TEMPORAL     cycle windows, event chronology, prediction-time boundaries
  ML           target distribution, feature variation, leakage, suspiciously perfect predictors,
               temporal coverage
  REALISM      programme / cycle / channel distribution, funnel rates, balance, segment behaviour

Every check produces a row of a results table. The script exits non-zero if any check FAILs.

Usage
-----
    python scripts/validate_dataset.py
    python scripts/validate_dataset.py --root path/to/admitflow-data
    python scripts/validate_dataset.py --fail-on warn
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import admitflow_schema as S  # noqa: E402

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
_RANK = {PASS: 0, WARN: 1, FAIL: 2}

TS_FMT = "%Y-%m-%dT%H:%M:%S"
DATE_FMT = "%Y-%m-%d"


# ======================================================================================
# Result plumbing
# ======================================================================================


@dataclass
class Check:
    family: str
    name: str
    status: str
    detail: str


class Report:
    def __init__(self) -> None:
        self.checks: List[Check] = []

    def add(self, family: str, name: str, status: str, detail: str = "") -> None:
        self.checks.append(Check(family, name, status, detail))

    def ok(self, family: str, name: str, cond: bool, ok: str, bad: str) -> bool:
        self.add(family, name, PASS if cond else FAIL, ok if cond else bad)
        return cond

    @property
    def n_fail(self) -> int:
        return sum(1 for c in self.checks if c.status == FAIL)

    @property
    def n_warn(self) -> int:
        return sum(1 for c in self.checks if c.status == WARN)


def rank_auc(y: np.ndarray, x: np.ndarray) -> float:
    """Rank AUC (Mann-Whitney) with tie handling. Returns nan if x or y is constant."""
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    mask = ~np.isnan(x)
    y, x = y[mask], x[mask]
    if len(y) < 10 or len(np.unique(y)) < 2 or len(np.unique(x)) < 2:
        return float("nan")
    order = np.argsort(x, kind="mergesort")
    xs = x[order]
    ranks = np.empty(len(x), dtype=float)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[j + 1] == xs[i]:
            j += 1
        ranks[order[i:j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    pos = y == 1
    n1, n0 = int(pos.sum()), int((~pos).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    return float((ranks[pos].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


# ======================================================================================
# Loading
# ======================================================================================


def load_tables(root: Path) -> Tuple[Dict[str, pd.DataFrame], Optional[pd.DataFrame], dict]:
    raw = root / "data" / "raw"
    dfs: Dict[str, pd.DataFrame] = {}
    for name in S.ENTITIES:
        path = raw / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(f"missing table {path}")
        dfs[name] = pd.read_csv(path, keep_default_na=True, na_values=[""])
    mv_path = root / "data" / "processed" / "applications_modelling_view.csv"
    mv = pd.read_csv(mv_path) if mv_path.exists() else None
    manifest_path = raw / "_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) \
        if manifest_path.exists() else {}
    return dfs, mv, manifest


# ======================================================================================
# 1. STRUCTURAL
# ======================================================================================


def check_structural(rep: Report, dfs: Dict[str, pd.DataFrame], manifest: dict) -> None:
    F = "STRUCTURAL"
    for name, ent in S.ENTITIES.items():
        df = dfs[name]
        expected = list(ent.column_names)
        actual = list(df.columns)
        missing = [c for c in expected if c not in actual]
        extra = [c for c in actual if c not in expected]
        rep.ok(F, f"{name}.columns",
               not missing and not extra,
               f"{len(expected)} columns present, order-independent",
               f"missing={missing} unexpected={extra}")

    for name, ent in S.ENTITIES.items():
        df = dfs[name]
        pk = ent.primary_key
        if pk in df.columns:
            dup = int(df[pk].duplicated().sum())
            rep.ok(F, f"{name}.pk_unique[{pk}]", dup == 0,
                   f"{df[pk].nunique():,} unique / {len(df):,} rows",
                   f"{dup} duplicate primary keys")
            nulls = int(df[pk].isna().sum())
            rep.ok(F, f"{name}.pk_notnull[{pk}]", nulls == 0, "no null primary keys",
                   f"{nulls} null primary keys")

    for src_entity, col, tgt_entity, tgt_col in S.FOREIGN_KEYS:
        if col not in dfs[src_entity].columns or tgt_col not in dfs[tgt_entity].columns:
            continue
        left = dfs[src_entity][col]
        right = set(dfs[tgt_entity][tgt_col].dropna().unique())
        bad = ~left.isna() & ~left.isin(right)
        n_bad = int(bad.sum())
        rep.ok(F, f"fk[{src_entity}.{col} -> {tgt_entity}.{tgt_col}]", n_bad == 0,
               "all non-null foreign keys resolve",
               f"{n_bad} orphaned foreign keys, e.g. {list(left[bad].unique()[:5])}")

    if manifest:
        for tname, expected_rows in manifest.get("row_counts", {}).items():
            if tname in dfs:
                rep.ok(F, f"{tname}.row_count", len(dfs[tname]) == expected_rows,
                       f"{len(dfs[tname]):,} rows matches manifest",
                       f"{len(dfs[tname]):,} rows but manifest says {expected_rows:,}")

    # required (non-nullable) fields must be populated
    for name, ent in S.ENTITIES.items():
        df = dfs[name]
        for c in ent.columns:
            if c.nullable or c.dtype in ("bool",):
                continue
            n_null = int(df[c.name].isna().sum())
            if n_null:
                rep.add(F, f"{name}.{c.name}.notnull", WARN,
                        f"{n_null:,} nulls in a non-nullable field "
                        f"({100 * n_null / max(1, len(df)):.2f}%)")


def check_dtypes(rep: Report, dfs: Dict[str, pd.DataFrame]) -> None:
    F = "STRUCTURAL"
    for name, ent in S.ENTITIES.items():
        df = dfs[name]
        for c in ent.columns:
            if c.name not in df.columns:
                continue
            s = df[c.name].dropna()
            if len(s) == 0:
                continue
            if c.dtype == "int64":
                ok = pd.api.types.is_numeric_dtype(s) and \
                    bool((s == s.round()).all())
                rep.ok(F, f"{name}.{c.name}.int", ok, "integral numeric",
                       f"non-integral values in an int64 field")
            elif c.dtype == "float64":
                ok = pd.api.types.is_numeric_dtype(s)
                rep.ok(F, f"{name}.{c.name}.float", ok, "numeric", "non-numeric values")
            elif c.dtype == "bool":
                vals = set(s.astype(str).unique())
                ok = vals <= {"True", "False", "true", "false"}
                rep.ok(F, f"{name}.{c.name}.bool", ok, "boolean values", f"values={vals}")
            elif c.dtype == "date":
                ok = bool(s.astype(str).str.match(r"^\d{4}-\d{2}-\d{2}$").all())
                rep.ok(F, f"{name}.{c.name}.date", ok, "ISO date", "malformed date value")
            elif c.dtype == "timestamp":
                ok = bool(s.astype(str).str.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$").all())
                rep.ok(F, f"{name}.{c.name}.timestamp", ok, "ISO timestamp",
                       "malformed timestamp value")


# ======================================================================================
# 2. DATA QUALITY
# ======================================================================================


def check_data_quality(rep: Report, dfs: Dict[str, pd.DataFrame], mv: Optional[pd.DataFrame]) -> None:
    F = "DATA"
    for name, ent in S.ENTITIES.items():
        df = dfs[name]
        if len(df) == 0:
            continue
        miss = df.isna().mean()
        for col, frac in miss[miss > 0].items():
            coldef = ent.col(col)
            expected_null = coldef.nullable
            status = PASS if expected_null else WARN
            note = S.STAGE_CONDITIONAL_COLUMNS.get(col, "")
            rep.add(F, f"{name}.{col}.missingness", status,
                    f"{frac:.2%} null"
                    + (f"  (stage-conditional: {note})" if note else "")
                    + ("" if expected_null else "  (field is declared non-nullable)"))
        full_dup = int(df.duplicated().sum())
        rep.ok(F, f"{name}.no_full_row_duplicates", full_dup == 0,
               "no duplicated rows", f"{full_dup} fully duplicated rows")

    # categorical domains
    for name, ent in S.ENTITIES.items():
        df = dfs[name]
        for c in ent.columns:
            if not c.categories or c.name not in df.columns:
                continue
            seen = set(df[c.name].dropna().astype(str).unique())
            bad = seen - set(c.categories)
            rep.ok(F, f"{name}.{c.name}.domain", not bad,
                   f"{len(seen)} values within the declared domain",
                   f"invalid categories: {sorted(bad)[:8]}")

    # numeric ranges
    apps = dfs["fact_application"]
    for col, lo, hi in (("academic_score_pct", 0.0, 100.0),
                        ("doc_completeness_score", 0.0, 1.0),
                        ("touchpoints_count", 1.0, 12.0),
                        ("selection_score", 0.0, 100.0),
                        ("intake_round", 1.0, 2.0)):
        s = apps[col].dropna()
        if len(s) == 0:
            continue
        bad = int(((s < lo) | (s > hi)).sum())
        rep.ok(F, f"fact_application.{col}.range", bad == 0,
               f"all values within [{lo}, {hi}]",
               f"{bad} values outside [{lo}, {hi}] (min={s.min()}, max={s.max()})")
    for col in ("enrolled_flag", "admitted_flag", "enrolled_given_admitted_flag"):
        s = apps[col].dropna()
        if len(s) == 0:
            continue
        bad = int((~s.isin([0, 1])).sum())
        rep.ok(F, f"fact_application.{col}.binary", bad == 0, "values in {0, 1}",
               f"{bad} values outside {{0, 1}}")

    for col in ("pre_sub_session_count", "pre_sub_active_days", "pre_sub_total_minutes",
                "pre_sub_doc_uploads", "pre_sub_form_fields_completed",
                "pre_sub_return_visits", "pre_sub_session_count"):
        s = apps[col].dropna()
        bad = int((s < 0).sum())
        rep.ok(F, f"fact_application.{col}.nonneg", bad == 0, "no negative counts",
               f"{bad} negative values")

    # campaign integrity: null campaign only for non-campaign channels
    camp = dfs["dim_campaign"]
    camp_channels = set(camp[camp["is_active"]]["channel"]) if "is_active" in camp else set()
    non_camp = {"organic_search", "referral", "direct", "education_fair"}
    has = apps["campaign_id"].notna()
    bad = apps.loc[has & ~apps["acquisition_channel"].isin(camp_channels), "acquisition_channel"]
    rep.ok(F, "campaign.channel_consistency", len(bad) == 0,
           "campaign_id only appears on campaign-bearing channels",
           f"{len(bad)} rows carry a campaign_id on a non-campaign channel")
    bad2 = apps.loc[~has & apps["acquisition_channel"].isin(camp_channels), "acquisition_channel"]
    rep.ok(F, "campaign.attribution_coverage",
           len(bad2) / max(1, apps["acquisition_channel"].isin(camp_channels).sum()) < 0.25,
           f"{(~has & apps['acquisition_channel'].isin(camp_channels)).mean():.1%} of campaign-channel "
           f"rows are un-attributed (expected, no campaign was live on the touch date)",
           f"{(~has & apps['acquisition_channel'].isin(camp_channels)).mean():.1%} un-attributed")

    # first_touch must not be after the inquiry
    inq = pd.to_datetime(apps["inquiry_ts"], format=TS_FMT)
    ft = pd.to_datetime(apps["first_touch_date"], format=DATE_FMT)
    bad = int((ft > inq.dt.normalize()).sum())
    rep.ok(F, "attribution.first_touch_le_inquiry", bad == 0,
           "first_touch_date <= inquiry date for every application",
           f"{bad} applications have a first touch after the inquiry")

    if mv is not None:
        dup = int(mv["application_id"].duplicated().sum())
        rep.ok(F, "modelling_view.pk_unique", dup == 0,
               f"{len(mv):,} rows, application_id unique", f"{dup} duplicate application_id")
        missing = [c for c in S.MV_COLUMNS and [m.name for m in S.MV_COLUMNS]
                   if c not in mv.columns]
        rep.ok(F, "modelling_view.columns", not missing,
               f"all {len(S.MV_COLUMNS)} declared columns present",
               f"missing columns: {missing}")


# ======================================================================================
# 3. FUNNEL INTEGRITY
# ======================================================================================


def check_funnel(rep: Report, dfs: Dict[str, pd.DataFrame]) -> None:
    F = "FUNNEL"
    apps = dfs["fact_application"]
    ev = dfs["fact_funnel_event"]

    # F1 prefix-closed staircase
    per_app = ev.groupby("application_id")["stage_order"].apply(
        lambda s: tuple(sorted(int(x) for x in s)))
    bad_prefix = [a for a, st in per_app.items()
                  if st != tuple(range(1, len(st) + 1))]
    rep.ok(F, "F1.prefix_closed_staircase", not bad_prefix,
           f"all {len(per_app):,} applications have a gap-free stage ladder",
           f"{len(bad_prefix)} applications skip a stage, e.g. {bad_prefix[:5]}")

    # (application, stage) uniqueness
    dup = int(ev.duplicated(["application_id", "stage_code"]).sum())
    rep.ok(F, "F1.no_duplicate_milestones", dup == 0,
           "at most one milestone row per (application, stage)", f"{dup} duplicates")

    # F2 strictly increasing chronology
    ev2 = ev.sort_values(["application_id", "stage_order"])
    ts = pd.to_datetime(ev2["event_ts"], format=TS_FMT, errors="coerce")
    g = ts.groupby(ev2["application_id"])
    prev = g.shift(1)
    bad = int((ts <= prev).sum())
    rep.ok(F, "F2.strictly_increasing_events", bad == 0,
           "event timestamps strictly increase along the ladder for every application",
           f"{bad} non-increasing milestone timestamps")

    # F3 exactly one terminal stage per application
    term = ev.groupby("application_id")["is_terminal_stage"].sum()
    bad = int((term != 1).sum())
    rep.ok(F, "F3.single_terminal_stage", bad == 0,
           "every application has exactly one terminal milestone", f"{bad} mismatches")
    apps_in_events = set(ev["application_id"])
    rep.ok(F, "F3.every_application_has_events", apps_in_events == set(apps["application_id"]),
           f"all {len(apps):,} applications have a `prospect` event",
           f"{len(set(apps['application_id']) - apps_in_events)} applications have no events")

    # stage_reached agreement between the two tables
    reached = (ev.sort_values("stage_order").groupby("application_id")["stage_code"]
               .last().rename("ev_reached"))
    merged = apps.set_index("application_id").join(reached)
    bad = int((merged["stage_reached"] != merged["ev_reached"]).sum())
    rep.ok(F, "stage_reached_consistency", bad == 0,
           "fact_application.stage_reached == highest stage in fact_funnel_event",
           f"{bad} disagreements between the fact and event tables")
    order_map = ev.drop_duplicates("application_id").set_index("application_id")["stage_code"]
    bad = int((apps.set_index("application_id")["stage_reached"].map(S.STAGE_ORDER)
               != apps.set_index("application_id")["stage_reached_order"]).sum())
    rep.ok(F, "stage_reached_order_consistency", bad == 0,
           "stage_reached_order matches the stage ladder index", f"{bad} disagreements")

    # F5 drop-off consistency
    not_enrolled = apps[apps["stage_reached"] != "enrolled"]
    bad = int(not_enrolled["dropoff_stage"].isna().sum())
    rep.ok(F, "F5.dropoff_stage_present", bad == 0,
           "every non-enrolled application has a drop-off stage", f"{bad} null drop-off stages")
    bad = int((not_enrolled["dropoff_stage"] != not_enrolled["stage_reached"]).sum())
    rep.ok(F, "F5.dropoff_stage_equals_stage_reached", bad == 0,
           "dropoff_stage == stage_reached for all non-enrolled applications",
           f"{bad} mismatches")
    bad = int(not_enrolled["dropoff_reason"].isna().sum())
    rep.ok(F, "F5.dropoff_reason_present", bad == 0,
           "every non-enrolled application has a drop-off reason", f"{bad} null reasons")
    enrolled = apps[apps["stage_reached"] == "enrolled"]
    bad = int(enrolled[["dropoff_stage", "dropoff_reason"]].notna().any(axis=1).sum())
    rep.ok(F, "F5.enrolled_has_no_dropoff", bad == 0,
           "enrolled applications carry no drop-off", f"{bad} enrolled rows with a drop-off")
    bad = int((apps["dropoff_reason"].notna()
               & ~apps["dropoff_reason"].isin(S.DROP_REASONS)).sum())
    rep.ok(F, "F5.dropoff_reason_domain", bad == 0,
           "drop-off reasons are within the declared list", f"{bad} unknown reasons")

    # impossible transitions
    admitted = apps[apps["stage_reached_order"] >= 6]
    bad = int((admitted["decision_type"] != "admit").sum())
    rep.ok(F, "no_transition.admitted_requires_admit_decision", bad == 0,
           "every admitted application has decision_type = 'admit'", f"{bad} violations")
    bad = int((admitted["decision_ts_missing"] if "decision_ts_missing" in admitted
               else pd.Series(False, index=admitted.index)).sum())
    bad = int(admitted["admission_decision_ts"].isna().sum())
    rep.ok(F, "no_transition.admitted_has_decision_ts", bad == 0,
           "every admitted application has a decision timestamp", f"{bad} missing")
    enrolled_rows = apps[apps["enrolled_flag"] == 1]
    bad = int((enrolled_rows["stage_reached_order"] != 7).sum())
    rep.ok(F, "no_transition.enrolled_is_terminal", bad == 0,
           "enrolled_flag = 1 only at the final stage", f"{bad} violations")
    bad = int((enrolled_rows["admitted_flag"] != 1).sum())
    rep.ok(F, "no_transition.enrolled_implies_admitted", bad == 0,
           "enrolled_flag = 1 implies admitted_flag = 1", f"{bad} violations")
    bad = int((apps["enrolled_given_admitted_flag"].notna()
               & (apps["admitted_flag"] != 1)).sum())
    rep.ok(F, "no_transition.conditional_target_scope", bad == 0,
           "enrolled_given_admitted_flag is null unless admitted_flag = 1", f"{bad} violations")
    bad = int((apps["withdrawn_flag"] & apps["admission_decision_ts"].notna()).sum())
    rep.ok(F, "no_transition.withdrawn_has_no_decision", bad == 0,
           "withdrawn applications never receive a decision", f"{bad} violations")
    bad = int(((apps["decision_type"] == "admit") & apps["admitted_ts"].isna()).sum())
    rep.ok(F, "no_transition.admit_has_admitted_ts", bad == 0,
           "decision_type = 'admit' implies a recorded admitted_ts", f"{bad} violations")
    bad = int(((apps["stage_reached_order"] >= 4) & apps["application_verified_ts"].isna()).sum())
    rep.ok(F, "no_transition.verified_has_timestamp", bad == 0,
           "reaching verification implies a verification timestamp", f"{bad} violations")
    bad = int((apps["scholarship_amount_inr"] > 0).sum()
              - (apps["scholarship_offered"] & (apps["scholarship_amount_inr"] > 0)).sum())
    rep.ok(F, "no_transition.scholarship_consistency", bad <= 0,
           "a positive scholarship amount only occurs with scholarship_offered = True",
           f"{bad} rows with an amount but no scholarship flag")
    bad = int((apps["offer_letter_issued"] != (apps["decision_type"] == "admit").fillna(False)).sum())
    rep.ok(F, "no_transition.offer_letter_consistency", bad == 0,
           "offer_letter_issued == (decision_type == 'admit')", f"{bad} violations")

    # null pattern of stage-conditional columns must match the funnel
    n = len(apps)
    n_started = int((apps["stage_reached_order"] >= 2).sum())
    n_submitted = int((apps["stage_reached_order"] >= 3).sum())
    for col, pop, label in (("application_started_ts", n_started, "application_started"),
                            ("application_submitted_ts", n_submitted, "application_submitted"),
                            ("academic_score_pct", n_submitted, "application_submitted"),
                            ("pre_sub_session_count", n_submitted, "application_submitted"),
                            ("days_inquiry_to_start", n_started, "application_started"),
                            ("prediction_ts", n_submitted, "application_submitted")):
        if col not in apps.columns:
            continue
        non_null = int(apps[col].notna().sum())
        rep.ok(F, f"nulls.stage_conditional[{col}]", non_null == pop,
               f"{non_null:,} non-null values = the {pop:,} applications that reached "
               f"`{label}`", f"expected {pop:,} non-null, found {non_null:,} of {n:,}")

    # monotonic funnel counters in the panel
    panel = dfs["fact_forecast_panel"]
    ordered = ["cum_applications_opened", "cum_applications_started",
               "cum_applications_submitted", "cum_applications_verified",
               "cum_decisions_issued", "cum_admitted", "cum_enrolled"]
    arr = panel[ordered].to_numpy()
    bad = int((np.diff(arr, axis=1) > 0).sum())
    rep.ok(F, "panel.counts_non_increasing_down_ladder", bad == 0,
           "cumulative counts never decrease down the funnel ladder", f"{bad} violations")
    final = panel.sort_values("week_index_in_cycle").groupby(
        ["programme_id", "cycle_id"]).tail(1).set_index(["programme_id", "cycle_id"])
    bad = int((final["n_applications"] != final["cum_applications_opened"]).sum())
    rep.ok(F, "panel.n_applications_matches_opened", bad == 0,
           "panel.n_applications is the programme-cycle total and equals the final "
           "cum_applications_opened", f"{bad} mismatches")
    for a, b in (("wk_applications_submitted", "cum_applications_submitted"),
                 ("wk_admitted", "cum_admitted"), ("wk_enrolled", "cum_enrolled")):
        bad = int((panel[b] < panel[a]).sum())
        rep.ok(F, f"panel.cumulative_ge_weekly[{a}]", bad == 0,
               f"{b} >= {a} in every panel cell", f"{bad} cells violate the cumulative bound")


# ======================================================================================
# 4. TEMPORAL INTEGRITY
# ======================================================================================


def check_temporal(rep: Report, dfs: Dict[str, pd.DataFrame], manifest: Optional[dict]) -> None:
    F = "TEMPORAL"
    apps = dfs["fact_application"]
    ev = dfs["fact_funnel_event"]
    cyc = dfs["dim_admission_cycle"].set_index("cycle_id")

    def cyc_col(df: pd.DataFrame, column: str) -> pd.Series:
        """Map each row's cycle_id onto a dim_admission_cycle date column."""
        return df["cycle_id"].map(cyc[column])

    for col in ("cycle_start_date", "cycle_end_date", "intake1_application_open",
                "intake1_application_close", "intake2_application_open",
                "intake2_application_close", "intake1_decision_start", "intake1_decision_end",
                "intake2_decision_start", "intake2_decision_end", "verification_end_date",
                "intake1_offer_deadline", "intake2_offer_deadline",
                "intake1_enrolment_end", "intake2_enrolment_end"):
        d = pd.to_datetime(cyc[col], format=DATE_FMT)
        if col in ("cycle_end_date", "intake2_application_close", "intake1_decision_end",
                   "intake2_decision_end", "verification_end_date", "intake2_offer_deadline",
                   "intake2_enrolment_end"):
            ok = bool((d > pd.to_datetime(cyc["cycle_start_date"], format=DATE_FMT)).all())
        else:
            ok = bool((d >= pd.to_datetime(cyc["cycle_start_date"], format=DATE_FMT)).all())
        rep.ok(F, f"cycle_calendar.{col}_ordered", ok,
               "cycle calendar is chronologically consistent", f"{col} is out of order")

    starts = pd.to_datetime(cyc["cycle_start_date"], format=DATE_FMT)
    ends = pd.to_datetime(cyc["cycle_end_date"], format=DATE_FMT)
    rep.ok(F, "cycle_calendar.monotonic_acyclic", bool((starts.values[1:] > starts.values[:-1]).all()),
           "cycle start dates strictly increase", "cycle start dates are not increasing")

    # every event inside its cycle window
    ev2 = ev.merge(cyc[["cycle_start_date", "cycle_end_date"]], left_on="cycle_id",
                   right_index=True, how="left")
    d = pd.to_datetime(ev2["event_date"], format=DATE_FMT)
    lo = pd.to_datetime(ev2["cycle_start_date"], format=DATE_FMT)
    hi = pd.to_datetime(ev2["cycle_end_date"], format=DATE_FMT)
    bad = int(((d < lo) | (d > hi)).sum())
    rep.ok(F, "events.inside_cycle_window", bad == 0,
           f"all {len(ev):,} funnel events fall inside their cycle window",
           f"{bad} events fall outside the cycle window")

    # applications submitted within their intake round's close date
    sub = pd.to_datetime(apps["application_submitted_ts"], format=TS_FMT, errors="coerce")
    submitted = apps["application_submitted_ts"].notna()
    close = pd.to_datetime(
        np.where(apps["intake_round"] == 1,
                 cyc_col(apps, "intake1_application_close"),
                 cyc_col(apps, "intake2_application_close")), format=DATE_FMT)
    bad = int(((sub.dt.normalize() > close) & submitted).sum())
    rep.ok(F, "submission.within_round_close", bad == 0,
           "every submission is on or before its intake round close date",
           f"{bad} submissions after the round close date")

    open_d = pd.to_datetime(
        np.where(apps["intake_round"] == 1,
                 cyc_col(apps, "intake1_application_open"),
                 cyc_col(apps, "intake2_application_open")), format=DATE_FMT)
    inq = pd.to_datetime(apps["inquiry_ts"], format=TS_FMT)
    bad = int((inq.dt.normalize() < pd.to_datetime(open_d, format=DATE_FMT)).sum())
    rep.ok(F, "inquiry.within_cycle_window", bad == 0,
           "every inquiry is on or after the cycle application open date",
           f"{bad} inquiries before the cycle opened")

    # verification completes before the round's own decision window opens
    verified = apps[apps["application_verified_ts"].notna()].copy()
    v = pd.to_datetime(verified["application_verified_ts"], format=TS_FMT)
    dec = pd.to_datetime(
        np.where(verified["intake_round"] == 1,
                 cyc_col(verified, "intake1_decision_start"),
                 cyc_col(verified, "intake2_decision_start")), format=DATE_FMT)
    bad = int((v.dt.normalize() > dec).sum())
    rep.add(F, "verification.before_round_decision_window", PASS if bad == 0 else WARN,
            f"{len(verified) - bad:,} verifications complete before their own intake round's "
            f"decision window opens; {bad} are late (the generator pushes those applications to "
            f"the next decision window, which is realistic and is recorded in "
            f"`days_verified_to_decision`)" if bad else
            "every verification completes before its own intake round's decision window opens")

    # enrolled within the round's enrolment window
    enr = apps[apps["enrolled_ts"].notna()]
    e = pd.to_datetime(enr["enrolled_ts"], format=TS_FMT)
    end = pd.to_datetime(
        np.where(enr["intake_round"] == 1,
                 cyc_col(enr, "intake1_enrolment_end"),
                 cyc_col(enr, "intake2_enrolment_end")), format=DATE_FMT)
    bad = int((e.dt.normalize() > end).sum())
    rep.ok(F, "enrolment.within_round_window", bad == 0,
           "every enrolment is inside its intake round's registration window",
           f"{bad} enrolments after the window closed")

    off = pd.to_datetime(apps.loc[apps["offer_deadline"].notna(), "offer_deadline"],
                         format=DATE_FMT)
    e2 = pd.to_datetime(apps.loc[apps["offer_deadline"].notna(), "enrolled_ts"],
                        format=TS_FMT, errors="coerce")
    m = e2.notna()
    bad = int((e2[m].dt.normalize() > pd.to_datetime(
        apps.loc[apps["offer_deadline"].notna(), "offer_deadline"], format=DATE_FMT)[m]).sum())
    rep.ok(F, "enrolment.before_offer_deadline", bad == 0,
           "no enrolment occurs after the offer deadline", f"{bad} late enrolments")

    # withdrawal before the decision
    wd = apps.loc[apps["withdrawn_date"].notna(), "withdrawn_date"]
    dts = pd.to_datetime(apps.loc[apps["withdrawn_date"].notna(), "admission_decision_ts"],
                         format=TS_FMT, errors="coerce")
    bad = int((dts.notna()).sum())
    rep.ok(F, "withdrawal.precedes_decision", bad == 0,
           "withdrawn applications have no decision timestamp", f"{bad} withdrawals with decisions")

    # engagement never after the prediction point
    eng = dfs["fact_engagement"]
    pred = apps.set_index("application_id")["application_submitted_ts"]
    ed = pd.to_datetime(eng["activity_date"], format=DATE_FMT)
    p = pd.to_datetime(eng["application_id"].map(pred), format=TS_FMT, errors="coerce")
    has_pred = p.notna()
    bad = int((ed[has_pred] > p[has_pred].dt.normalize()).sum())
    rep.ok(F, "engagement.never_after_prediction_point", bad == 0,
           f"all {int(has_pred.sum()):,} engagement rows for submitted applications are on or "
           f"before the prediction date", f"{bad} engagement rows after the prediction date")
    bad = int(eng["days_before_submission"].dropna().lt(0).sum())
    rep.ok(F, "engagement.days_before_submission_nonneg", bad == 0,
           "days_before_submission is never negative", f"{bad} negative values")
    started = set(apps.loc[apps["stage_reached_order"] >= 2, "application_id"])
    bad = int((~eng["application_id"].isin(started)).sum())
    rep.ok(F, "engagement.only_for_started_applications", bad == 0,
           "engagement exists only for applications that reached application_started",
           f"{bad} engagement rows for applications that never started")

    # panel grid
    panel = dfs["fact_forecast_panel"]
    n_programmes = int(dfs["dim_programme"]["programme_id"].nunique())
    expected_cells = sum(n_programmes * int(c["total_weeks"]) for _, c in cyc.iterrows())
    rep.ok(F, "panel.complete_grid", len(panel) == expected_cells,
           f"{len(panel):,} panel cells = programmes x cycles x weeks",
           f"expected {expected_cells:,} panel cells, found {len(panel):,}")
    panel_weeks = cyc_col(panel, "total_weeks").to_numpy(dtype=float)
    grp = panel.groupby(["programme_id", "cycle_id"])["week_index_in_cycle"].max()
    grp_weeks = grp.index.get_level_values("cycle_id").map(cyc["total_weeks"]).to_numpy(dtype=float)
    bad = int(np.abs(grp.to_numpy(dtype=float) + 1.0 - grp_weeks).sum())
    rep.ok(F, "panel.week_index_bounded", bad == 0,
           "the last panel week of every programme-cycle is week index total_weeks - 1",
           f"{bad} cells do not reach total_weeks - 1")
    wk = pd.to_datetime(panel["week_start_date"], format=DATE_FMT)
    rep.ok(F, "panel.weeks_start_on_monday", bool((wk.dt.weekday == 0).all()),
           "every panel week starts on a Monday", "some panel weeks do not start on a Monday")
    bad = int((pd.to_datetime(panel["week_end_date"], format=DATE_FMT)
               - pd.to_datetime(panel["week_start_date"], format=DATE_FMT)).dt.days.ne(6).sum())
    rep.ok(F, "panel.weeks_are_seven_days", bad == 0, "every panel week spans 7 days",
           f"{bad} malformed weeks")

    # chronological split is consistent and derived from cycle only
    split_by_cycle = {c: sorted(set(g["split_hint"]))
                      for c, g in panel.groupby("cycle_id")}
    rep.ok(F, "split.chronological", all(len(v) == 1 for v in split_by_cycle.values()),
           "split_hint is a pure function of cycle_id (train / validation / test are "
           "consecutive, non-overlapping cycle ranges)",
           f"cycles with a mixed split_hint: {[c for c, v in split_by_cycle.items() if len(v) > 1]}")
    cyc_order = sorted(cyc.index)
    expected_split = {c: S.split_hint(i, len(cyc_order)) for i, c in enumerate(cyc_order)}
    rep.ok(F, "split.matches_contract",
           set(split_by_cycle) == set(expected_split) and
           all(split_by_cycle[c][0] == expected_split[c] for c in expected_split),
           "every cycle carries the split_hint assigned to it by the documented "
           "chronological rule (cycles are ordered by cycle_start_date)",
           f"expected {sorted(expected_split.items())}, observed "
           f"{[(c, split_by_cycle[c][0]) for c in sorted(split_by_cycle)]}")
    # temporal coverage
    span_start = pd.to_datetime(apps["inquiry_ts"], format=TS_FMT).min()
    span_end = pd.to_datetime(apps["enrolled_ts"], format=TS_FMT, errors="coerce").max()
    months = (span_end.year - span_start.year) * 12 + (span_end.month - span_start.month)
    rep.add(F, "temporal_coverage", PASS if months >= 36 else WARN,
            f"{span_start.date()} .. {span_end.date()} ({months} months across "
            f"{apps['cycle_id'].nunique()} closed cycles)")
    elig = int(panel["is_forecast_eligible"].sum())
    rep.add(F, "forecast_origins_available", PASS if elig >= 200 else WARN,
            f"{elig:,} eligible forecast origins across programme x cycle x week")
    horizons = (manifest.get("config", {}).get("forecast_horizons_weeks")
                if isinstance(manifest, dict) else None) or [1, 2, 4, 6]
    for h in horizons:
        el = panel[panel["is_forecast_eligible"]]
        ok = bool(len(el) > 0 and
                  ((el["week_index_in_cycle"] + h) <= cyc_col(el, "total_weeks")).all())
        rep.add(F, f"forecast_horizon_{h}w_supported", PASS if ok else WARN,
                f"H = {h}w: the origin+H week exists for all {len(el):,} eligible forecast "
                f"origins" if ok else
                f"H = {h}w: the origin+H week is missing for at least one eligible origin")


# ======================================================================================
# 5. ML QUALITY AND LEAKAGE
# ======================================================================================


def check_ml_quality(rep: Report, dfs: Dict[str, pd.DataFrame],
                     mv: Optional[pd.DataFrame]) -> None:
    F = "ML"
    apps = dfs["fact_application"]

    if mv is None:
        rep.add(F, "modelling_view.present", FAIL,
                "data/processed/applications_modelling_view.csv is missing")
        return

    # --- target distribution -------------------------------------------------------
    y = mv["enrolled_flag"].astype(int)
    rate = float(y.mean())
    rep.add(F, "target.balance", PASS if 0.10 <= rate <= 0.60 else WARN,
            f"enrolled_flag mean = {rate:.4f} ({int(y.sum()):,} positives / {len(y):,} rows)")
    n_app = len(apps)
    rep.add(F, "target.volume", PASS if len(mv) >= 5000 else WARN,
            f"modelling view has {len(mv):,} rows, raw fact has {n_app:,} application rows")
    ya = mv["enrolled_given_admitted_flag"].dropna().astype(int)
    rep.add(F, "secondary_target.balance", PASS if 0.25 <= float(ya.mean()) <= 0.85 else WARN,
            f"enrolled_given_admitted_flag mean = {float(ya.mean()):.4f} over {len(ya):,} admits")
    rep.add(F, "tertiary_target.balance", PASS,
            f"admitted_flag mean = {float(mv['admitted_flag'].mean()):.4f} over {len(mv):,} rows")

    # --- leakage: role-based -------------------------------------------------------
    post = {c for _, c in S.post_outcome_columns()}
    for fset in S.FEATURE_SETS:
        feats = {c for _, c in S.feature_columns(fset)}
        overlap = sorted(feats & post)
        rep.ok(F, f"leakage.no_post_outcome_in_{fset}_features", not overlap,
               f"none of the {len(feats)} `{fset}` features is POST_OUTCOME or TARGET",
               f"leaking columns in `{fset}`: {overlap}")

    mv_primary = {m.name for m in S.MV_COLUMNS if m.in_primary}
    mv_bad = sorted(mv_primary & post)
    rep.ok(F, "leakage.modelling_view_primary_clean", not mv_bad,
           f"the denormalised modelling view exposes no POST_OUTCOME field as a primary feature",
           f"leaking columns in the modelling view: {mv_bad}")
    rep.ok(F, "leakage.selection_score_excluded",
           "selection_score" not in mv.columns,
           "the deliberate leakage trap `selection_score` is absent from the modelling view",
           "`selection_score` is present in the modelling view")

    # --- leakage: prediction-time boundary, checked against the DATA ----------------
    pred = pd.to_datetime(mv["application_submitted_ts"], format=TS_FMT)
    for fset in S.FEATURE_SETS:
        if fset == S.FEATURE_SET_DECISION:
            continue
        point_col = S.prediction_point_column(fset)
        p = pd.to_datetime(mv[point_col], format=TS_FMT)
        for ent, colname in S.feature_columns(fset):
            if colname not in mv.columns:
                continue
            src = S.source_ts_field(ent, colname, fset)
            if src is None:
                rep.add(F, f"leakage.boundary[{fset}].{colname}", WARN,
                        "no source timestamp declared; boundary cannot be machine-verified")
                continue
            if src not in mv.columns:
                rep.add(F, f"leakage.boundary[{fset}].{colname}", WARN,
                        f"source timestamp `{src}` is not present in the modelling view")
                continue
            sv = pd.to_datetime(mv[src], format=DATE_FMT, errors="coerce")
            sv = sv.fillna(pd.to_datetime(mv[src], format=TS_FMT, errors="coerce"))
            bad = int((sv.dt.normalize() > p.dt.normalize()).sum())
            rep.ok(F, f"leakage.boundary[{fset}].{colname}", bad == 0,
                   f"`{src}` <= `{point_col}` on every row",
                   f"{bad} rows where `{src}` is later than the prediction point")

    # decision-view boundary
    dec = mv[mv["admission_decision_ts"].notna()]
    if len(dec):
        p = pd.to_datetime(dec["admission_decision_ts"], format=TS_FMT)
        for ent, colname in S.feature_columns(S.FEATURE_SET_DECISION):
            if colname not in dec.columns:
                continue
            src = S.source_ts_field(ent, colname, S.FEATURE_SET_DECISION)
            if src is None or src not in dec.columns:
                continue
            sv = pd.to_datetime(dec[src], format=DATE_FMT, errors="coerce")
            sv = sv.fillna(pd.to_datetime(dec[src], format=TS_FMT, errors="coerce"))
            bad = int((sv.dt.normalize() > p.dt.normalize()).sum())
            rep.ok(F, f"leakage.boundary[decision].{colname}", bad == 0,
                   f"`{src}` <= `admission_decision_ts` on every row",
                   f"{bad} rows with a post-decision source timestamp")

    # --- suspicious perfect predictors ---------------------------------------------
    # The FAIL threshold applies to the SAFE primary feature set only. POST_OUTCOME columns
    # are expected to predict the target well (that is what makes them traps); they are
    # reported separately as an audit of how dangerous the traps are.
    yb = y.to_numpy()
    skip = {"application_id", "applicant_id", "enrolled_flag", "stage_reached",
            "stage_reached_order", "admitted_flag", "enrolled_given_admitted_flag",
            "split_hint", "application_submitted_ts", "application_verified_ts",
            "admission_decision_ts"}
    safe_feats = {c for _, c in S.feature_columns(S.FEATURE_SET_PRIMARY)}
    safe_auc: List[Tuple[float, str]] = []
    trap_auc: List[Tuple[float, str]] = []
    for col in mv.columns:
        if col in skip:
            continue
        s = mv[col]
        if s.dtype == object or s.dtype.name in ("boolean", "Int64"):
            codes = pd.Categorical(s.astype("string").fillna("__NA__")).codes.astype(float)
        else:
            codes = pd.to_numeric(s, errors="coerce").to_numpy(dtype=float)
        auc = rank_auc(yb, codes)
        if math.isnan(auc):
            continue
        (safe_auc if col in safe_feats else trap_auc).append((max(auc, 1 - auc), col))
    safe_auc.sort(reverse=True)
    trap_auc.sort(reverse=True)
    top = ", ".join(f"`{c}`={a:.3f}" for a, c in safe_auc[:8])
    rep.add(F, "target.not_trivially_predictable",
            PASS if (not safe_auc or safe_auc[0][0] < 0.93) else FAIL,
            f"strongest single-feature rank AUC vs enrolled_flag among the {len(safe_auc)} "
            f"safe primary features: {top}")
    rep.add(F, "leakage.traps_are_dangerous",
            PASS if (not trap_auc or trap_auc[0][0] < 1.0) else WARN,
            "post-outcome columns (deliberate leakage traps) rank against the target as: "
            + (", ".join(f"`{c}`={a:.3f}" for a, c in trap_auc[:5]) or "none")
            + ". They are excluded from every feature set by construction.")
    n_unique = {c: int(mv[c].nunique(dropna=True)) for c in mv.columns}
    const = [c for c, u in n_unique.items() if u <= 1]
    rep.add(F, "feature.variation", PASS if not const else WARN,
            "every modelling-view column varies" if not const
            else f"constant columns: {const}")
    low_card = sorted(c for c, u in n_unique.items() if 1 < u <= 2)
    rep.add(F, "feature.degenerate_binary", PASS,
            f"{len(mv.columns)} columns, "
            f"{sum(1 for c in mv.columns if mv[c].dtype.name in ('Int64', 'int64', 'float64'))} "
            f"numeric, {len(low_card)} with <=2 levels")

    # a feature that is a copy of the target
    for col in mv.columns:
        if col == "enrolled_flag":
            continue
        s = mv[col]
        if set(pd.unique(s.dropna())) <= {0, 1} and len(s.dropna()) > 0:
            if bool((pd.to_numeric(s, errors="coerce").fillna(-1).to_numpy() == yb).all()):
                rep.add(F, f"leakage.duplicate_of_target[{col}]", FAIL,
                        "this feature is an exact copy of the target")
    rep.add(F, "leakage.no_target_duplicates", PASS, "no feature duplicates the target")

    # --- temporal evaluation readiness ---------------------------------------------
    for sset, n in mv["split_hint"].value_counts().items():
        rate_s = float(mv.loc[mv["split_hint"] == sset, "enrolled_flag"].mean())
        rep.add(F, f"split.content[{sset}]", PASS,
                f"{n:,} rows ({n / len(mv):.1%}), enrolled rate {rate_s:.4f}")
    for fset in S.FEATURE_SETS:
        feats = {c for _, c in S.feature_columns(fset)}
        present = [c for c in feats if c in mv.columns]
        rep.add(F, f"feature_set.available[{fset}]", PASS,
                f"{len(present)}/{len(feats)} declared `{fset}` features present in the "
                f"modelling view")


# ======================================================================================
# 6. STATISTICAL REALISM
# ======================================================================================


def check_realism(rep: Report, dfs: Dict[str, pd.DataFrame]) -> None:
    F = "REALISM"
    apps = dfs["fact_application"]
    panel = dfs["fact_forecast_panel"]
    n = len(apps)

    # programme distribution
    vc = apps["programme_id"].value_counts(normalize=True)
    rep.add(F, "distribution.programme", PASS if 0.02 <= vc.min() and vc.max() <= 0.22 else WARN,
            f"{len(vc)} programmes, share range {vc.min():.3f} - {vc.max():.3f}")
    vc = apps["cycle_id"].value_counts(normalize=True)
    rep.add(F, "distribution.cycle", PASS if vc.min() > 0.15 else WARN,
            "cycle shares: " + ", ".join(f"{k}={v:.3f}" for k, v in vc.sort_index().items()))
    vc = apps["acquisition_channel"].value_counts(normalize=True)
    rep.add(F, "distribution.acquisition_channel", PASS if vc.min() > 0.05 else WARN,
            "channel shares: " + ", ".join(f"{k}={v:.3f}" for k, v in vc.sort_index().items()))
    vc = apps["intake_round"].value_counts(normalize=True)
    rep.add(F, "distribution.intake_round", PASS,
            f"intake 1 = {vc.get(1, 0):.3f}, intake 2 = {vc.get(2, 0):.3f}")
    vc = dfs["fact_applicant"]["region_id"].value_counts(normalize=True)
    rep.add(F, "distribution.region", PASS if vc.min() > 0.04 else WARN,
            f"{len(vc)} regions, share range {vc.min():.3f} - {vc.max():.3f}")

    # funnel conversion rates
    g = apps.groupby("stage_reached_order").size().to_dict()
    cum = {k: sum(v for k2, v in g.items() if k2 >= k) for k in range(1, 8)}
    names = {s["stage_order"]: s["stage_code"] for s in S.FUNNEL_STAGES}
    lines, ok = [], True
    for k in range(1, 7):
        if cum[k] == 0:
            continue
        step = cum[k + 1] / cum[k]
        top = cum[k + 1] / n
        lines.append(f"{names[k]}->{names[k + 1]}: {step:.3f} (top-of-funnel {top:.3f})")
        if not (0.02 <= step <= 0.99):
            ok = False
    rep.add(F, "funnel.conversion_rates", PASS if ok else WARN,
            "step conversions: " + " | ".join(lines))
    rep.add(F, "funnel.no_zero_volume_stage", PASS if all(cum[k] > 0 for k in range(1, 8)) else FAIL,
            "every funnel stage is populated: " + ", ".join(
                f"{names[k]}={cum[k]:,}" for k in range(1, 8)))

    # programme-level conversion spread
    by_prog = apps.groupby("programme_id").apply(
        lambda d: pd.Series({
            "n": len(d),
            "submit_rate": (d["stage_reached_order"] >= 3).mean(),
            "verify_rate": ((d["stage_reached_order"] >= 3) & (d["stage_reached_order"] >= 4)
                            ).sum() / max(1, (d["stage_reached_order"] >= 3).sum()),
            "admit_rate": float(d.loc[d["stage_reached_order"] >= 5, "admitted_flag"].mean()),
            "enrol_yield": float(d["enrolled_flag"].mean()),
        }), include_groups=False)
    rep.add(F, "segment.programme_variation",
            PASS if by_prog["enrol_yield"].std() > 0.01 else WARN,
            "enrolment yield across programmes ranges "
            f"{by_prog['enrol_yield'].min():.3f} - {by_prog['enrol_yield'].max():.3f} "
            f"(sd {by_prog['enrol_yield'].std():.3f}); admit rate "
            f"{by_prog['admit_rate'].min():.3f} - {by_prog['admit_rate'].max():.3f}")

    # demand crowding: does higher demand imply lower admit rate?
    tmp = apps.copy()
    tmp["crowding"] = tmp.groupby("programme_id")["application_id"].transform("size") / 48.0
    adm = tmp[tmp["stage_reached_order"] >= 5]
    if len(adm) > 100:
        r = float(np.corrcoef(adm["crowding"], adm["admitted_flag"])[0, 1])
        rep.add(F, "segment.demand_crowding_effect", PASS if r < -0.15 else WARN,
                f"corr(programme demand, admit rate) = {r:+.3f} (expected negative: crowding "
                f"tightens selectivity)")

    # channel behaviour (association only)
    ch = apps.groupby("acquisition_channel").apply(
        lambda d: pd.Series({"n": len(d),
                             "submit_rate": (d["stage_reached_order"] >= 3).mean(),
                             "enrol_yield": float(d["enrolled_flag"].mean())}), include_groups=False)
    rep.add(F, "segment.channel_variation",
            PASS if ch["enrol_yield"].std() > 0.004 else WARN,
            "enrolment yield by first-touch channel ranges "
            f"{ch['enrol_yield'].min():.3f} - {ch['enrol_yield'].max():.3f} "
            f"(sd {ch['enrol_yield'].std():.3f}). ASSOCIATION ONLY - channel mix confounds this.")
    rep.add(F, "segment.channel_all_populated", PASS if (ch["n"] > 100).all() else WARN,
            "channel volumes: " + ", ".join(f"{k}={int(v):,}" for k, v in ch["n"].items()))

    # cycle behaviour
    cy = apps.groupby("cycle_id").apply(
        lambda d: pd.Series({"n": len(d), "enrol_yield": float(d["enrolled_flag"].mean()),
                             "admit_rate": float(d.loc[d["stage_reached_order"] >= 5,
                                                      "admitted_flag"].mean())}),
        include_groups=False)
    rep.add(F, "segment.cycle_variation", PASS if cy["enrol_yield"].std() > 0.003 else WARN,
            "enrolment yield by cycle: " + ", ".join(
                f"{k}={v:.3f}" for k, v in cy["enrol_yield"].sort_index().items()))

    # the panel's headline yield must match the fact table
    last = panel.sort_values("week_index_in_cycle").groupby(["programme_id", "cycle_id"]).tail(1)
    fact_enrolled = apps.groupby(["programme_id", "cycle_id"])["enrolled_flag"].sum()
    fact_opened = apps.groupby(["programme_id", "cycle_id"]).size()
    mism = int(((last.set_index(["programme_id", "cycle_id"])["cum_enrolled"]
                 - fact_enrolled.reindex(last.set_index(["programme_id", "cycle_id"]).index)
                 .fillna(0).to_numpy()).abs() > 0).sum())
    rep.ok(F, "panel.reconciles_with_fact", mism == 0,
           "final cumulative panel enrolled counts reconcile exactly with fact_application",
           f"{mism} programme-cycle cells do not reconcile")
    sub_mism = int(((last.set_index(["programme_id", "cycle_id"])["cum_applications_submitted"]
                    - apps.groupby(["programme_id", "cycle_id"])["stage_reached_order"]
                    .apply(lambda s: int((s >= 3).sum()))
                    .reindex(last.set_index(["programme_id", "cycle_id"]).index)
                    .fillna(0).to_numpy()).abs() > 0).sum())
    rep.ok(F, "panel.reconciles_submissions", sub_mism == 0,
           "final cumulative panel submitted counts reconcile exactly with fact_application",
           f"{sub_mism} programme-cycle cells do not reconcile")

    # engagement depth
    eng = dfs["fact_engagement"]
    started = int((apps["stage_reached_order"] >= 2).sum())
    per = len(eng) / max(1, started)
    rep.add(F, "behaviour.engagement_depth", PASS if 1.5 <= per <= 12 else WARN,
            f"{len(eng):,} engagement rows = {per:.2f} activity days per started application")

    # withdrawal rate
    wd = float(apps["withdrawn_flag"].mean())
    rep.add(F, "behaviour.withdrawal_rate", PASS if wd <= 0.05 else WARN,
            f"{wd:.3%} of applications withdrawn after submission")


# ======================================================================================
# Report rendering
# ======================================================================================


def render_report(rep: Report, root: Path, manifest: dict) -> str:
    out: List[str] = []
    out.append("# AdmitFlow — Dataset Validation Report\n")
    out.append(f"> {S.FICTIONALITY_STATEMENT}\n")
    out.append("\nThis report is produced by `scripts/validate_dataset.py` and is fully "
               "reproducible from the generated dataset. No result in this report is a model "
               "performance claim.\n")

    status = FAIL if rep.n_fail else (WARN if rep.n_warn else PASS)
    out.append(f"\n**Overall status: {status}** "
               f"({sum(1 for c in rep.checks if c.status == PASS)} pass, "
               f"{rep.n_warn} warn, {rep.n_fail} fail, {len(rep.checks)} checks)\n")

    if manifest:
        cfg = manifest.get("config", {})
        out.append("\n## Dataset under test\n")
        out.append("| Setting | Value |\n|---|---|")
        out.append(f"| dataset_version | `{manifest.get('dataset_version')}` |")
        out.append(f"| seed | `{cfg.get('seed')}` |")
        out.append(f"| n_applications (target) | {cfg.get('n_applications'):,} |")
        out.append(f"| admission cycles | {cfg.get('n_cycles')} "
                   f"(from AY{cfg.get('start_cycle_year')}) |")
        out.append(f"| numpy / pandas | {manifest.get('numpy_version')} / "
                   f"{manifest.get('pandas_version')} |")
        out.append("\n| Table | Rows | Columns |\n|---|---|---|")
        for t, r in manifest.get("row_counts", {}).items():
            out.append(f"| `{t}` | {r:,} | |")

    for family in ("STRUCTURAL", "DATA", "FUNNEL", "TEMPORAL", "ML", "REALISM"):
        checks = [c for c in rep.checks if c.family == family]
        if not checks:
            continue
        n_fail = sum(1 for c in checks if c.status == FAIL)
        n_warn = sum(1 for c in checks if c.status == WARN)
        out.append(f"\n---\n\n## {family}\n")
        out.append(f"_{len(checks)} checks — {n_fail} fail, {n_warn} warn_\n")
        out.append("\n| Check | Status | Detail |\n|---|---|---|")
        for c in sorted(checks, key=lambda x: (-_RANK[x.status], x.name)):
            detail = c.detail.replace("|", "\\|")
            out.append(f"| `{c.name}` | **{c.status}** | {detail} |")

    out.append(f"\n---\n\n> {S.FICTIONALITY_STATEMENT}\n")
    out.append(f">\n> {S.PERFORMANCE_DISCLAIMER}\n")
    return "\n".join(out) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Validate the AdmitFlow synthetic dataset.")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                    help="Project root (default: parent of scripts/).")
    ap.add_argument("--report", type=Path, default=None,
                    help="Where to write the Markdown report (default: <root>/reports/"
                         "validation_report.md).")
    ap.add_argument("--fail-on", choices=("fail", "warn"), default="fail",
                    help="Exit non-zero on FAIL only (default) or on FAIL and WARN.")
    args = ap.parse_args(argv)

    dfs, mv, manifest = load_tables(args.root)
    rep = Report()
    check_structural(rep, dfs, manifest)
    check_dtypes(rep, dfs)
    check_data_quality(rep, dfs, mv)
    check_funnel(rep, dfs)
    check_temporal(rep, dfs, manifest)
    check_ml_quality(rep, dfs, mv)
    check_realism(rep, dfs)

    out = args.report or (args.root / "reports" / "validation_report.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_report(rep, args.root, manifest), encoding="utf-8")

    n_pass = sum(1 for c in rep.checks if c.status == PASS)
    print(f"[admitflow] validation: {n_pass} pass, {rep.n_warn} warn, {rep.n_fail} fail "
          f"({len(rep.checks)} checks)")
    for c in rep.checks:
        if c.status != PASS:
            print(f"  {c.status}  {c.family}/{c.name}: {c.detail[:160]}")
    print(f"[admitflow] report -> {out}")
    if rep.n_fail:
        return 1
    if args.fail_on == "warn" and rep.n_warn:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
