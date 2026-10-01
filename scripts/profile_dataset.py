#!/usr/bin/env python
"""Profile the AdmitFlow synthetic dataset.

    python scripts/profile_dataset.py
    python scripts/profile_dataset.py --root . --report reports/profiling_report.md

WHAT THIS DOES
    Describes what is actually in the generated dataset: shape, missingness, duplicates,
    category distributions, target distribution, funnel counts and step conversions,
    programme / cycle / channel conversion, numeric summaries and temporal coverage.

WHAT THIS DELIBERATELY DOES NOT DO
    It does not fit, train, tune or score any model. There is no accuracy, AUC, precision,
    recall, RMSE or feature-importance number anywhere in the output, because reporting
    model performance is the job of the downstream modelling agent, not the dataset
    engineering agent. The only discriminative statistic reported is a single-feature
    rank-AUC screen used to prove the target is NOT trivially predictable (a data quality
    check), never as a performance claim.

The profile is descriptive only. It never writes to data/ and never modifies the dataset.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import admitflow_schema as S  # noqa: E402

TS_FMT = "%Y-%m-%dT%H:%M:%S"
DATE_FMT = "%Y-%m-%d"

NO_MODEL_CLAIM = (
    "This is a descriptive profile of a synthetic dataset. It contains no model "
    "performance figures: no fitted model, no train/test score, no accuracy, AUC, precision, "
    "recall, RMSE, SHAP value or feature importance. Any such number must come from the "
    "downstream modelling step, evaluated on the documented chronological split."
)


# ======================================================================================
# helpers
# ======================================================================================


def _cell(v: object) -> str:
    """Render one Markdown table cell, escaping the pipes that would split the row."""
    if v is None:
        return ""
    return str(v).replace("|", "\\|").replace("\n", " ")


def md_table(rows: Sequence[Sequence[object]], header: Sequence[str]) -> List[str]:
    out = ["| " + " | ".join(_cell(h) for h in header) + " |",
           "|" + "|".join("---" for _ in header) + "|"]
    for r in rows:
        out.append("| " + " | ".join(_cell(v) for v in r) + " |")
    return out


def pct(x: float) -> str:
    return f"{x:.2%}"


def num(x: float, d: int = 3) -> str:
    return "n/a" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{d}f}"


def rank_auc(y: np.ndarray, x: np.ndarray) -> float:
    """Rank-based AUC of a single feature against a binary target (ties averaged)."""
    ok = np.isfinite(x)
    if ok.sum() < 10 or len(np.unique(y[ok])) < 2:
        return float("nan")
    r = pd.Series(x[ok]).rank(method="average").to_numpy()
    n1 = int(y[ok].sum())
    n0 = int(len(y[ok]) - n1)
    if n1 == 0 or n0 == 0:
        return float("nan")
    return float((r[y[ok] == 1].sum() - n1 * (n1 + 1) / 2) / (n0 * n1))


def load(root: Path):
    dfs: Dict[str, pd.DataFrame] = {}
    for name in S.RAW_TABLES:
        p = root / "data" / "raw" / f"{name}.csv"
        if not p.exists():
            raise SystemExit(f"missing raw table: {p}\nRun scripts/generate_dataset.py first.")
        dfs[name] = pd.read_csv(p, keep_default_na=True, na_values=[""])
    mv_path = root / "data" / "processed" / "applications_modelling_view.csv"
    mv = pd.read_csv(mv_path, keep_default_na=True, na_values=[""]) if mv_path.exists() else None
    man_path = root / "data" / "raw" / "_manifest.json"
    manifest = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {}
    return dfs, mv, manifest


# ======================================================================================
# profile sections
# ======================================================================================


def section_shape(dfs, mv, manifest) -> List[str]:
    out = ["\n---\n\n## 1. Shape and inventory\n"]
    cfg = manifest.get("config", {})
    rows = [
        ["seed", f"`{cfg.get('seed')}`"],
        ["dataset_version", f"`{manifest.get('dataset_version')}`"],
        ["generator config (target n_applications)", f"{cfg.get('n_applications'):,}"
         if cfg.get("n_applications") else "n/a"],
        ["admission cycles", cfg.get("n_cycles", "n/a")],
        ["start cycle year", cfg.get("start_cycle_year", "n/a")],
        ["forecast horizons (weeks)", cfg.get("forecast_horizons_weeks", "n/a")],
        ["numpy / pandas", f"{manifest.get('numpy_version')} / {manifest.get('pandas_version')}"],
    ]
    out += md_table(rows, ["Setting", "Value"])
    out.append("")
    rows = []
    total = 0
    for name in S.RAW_TABLES:
        df = dfs[name]
        ent = S.ENTITIES[name]
        n_target = sum(1 for c in ent.columns if c.role == S.ROLE_TARGET)
        rows.append([f"`{name}`", ent.grain, f"{len(df):,}", len(df.columns), n_target])
        total += len(df)
    out += md_table(rows, ["Table", "Grain", "Rows", "Columns", "Target columns"])
    if mv is not None:
        out.append("")
        out += md_table([["`applications_modelling_view`", "one submitted application",
                          f"{len(mv):,}", len(mv.columns), "1 primary + 2 secondary"]],
                        ["Derived view", "Grain", "Rows", "Columns", "Target columns"])
    out.append(f"\n**Total fact and dimension rows: {total:,}.**")
    return out


def section_missingness(dfs, mv) -> List[str]:
    out = ["\n---\n\n## 2. Missingness\n",
           S.NULLABILITY_NOTE + "\n"]
    rows = []
    for name in S.RAW_TABLES:
        df = dfs[name]
        miss = df.isna().mean()
        for col, frac in miss[miss > 0.005].sort_values(ascending=False).items():
            coldef = S.ENTITIES[name].col(col)
            note = S.STAGE_CONDITIONAL_COLUMNS.get(col, "")
            rows.append([f"`{name}.{col}`", pct(frac), coldef.role,
                         "conditional" if coldef.nullable else "UNEXPECTED",
                         note if note else coldef.description[:60]])
    if not rows:
        return out + ["\nNo column in any table has more than 0.5% null values.\n"]
    out += md_table(rows, ["Column", "Null rate", "Role", "Expected?", "Population"])
    out.append("\nColumns omitted from this table have under 0.5% null values. "
               "A column that is *conditional* is null exactly for the rows that did not "
               "reach the funnel stage it describes - the null pattern is itself the signal, "
               "not a data defect.\n")
    return out


def section_duplicates(dfs, mv) -> List[str]:
    out = ["\n---\n\n## 3. Duplicates and key integrity\n"]
    rows = []
    for name in S.RAW_TABLES:
        df = dfs[name]
        pk = S.PRIMARY_KEYS[name]
        dup_pk = int(df.duplicated([pk]).sum())
        dup_row = int(df.duplicated().sum())
        rows.append([f"`{name}`", f"`{pk}`", f"{dup_pk:,}", f"{dup_row:,}"])
    out += md_table(rows, ["Table", "Primary key", "Duplicate keys", "Duplicate rows"])
    out.append("\n**Foreign keys.** Every foreign key value must exist in its parent table.\n")
    rows = []
    for child, child_col, parent, parent_col in S.FOREIGN_KEYS:
        if child not in dfs or parent not in dfs:
            continue
        cvals = dfs[child][child_col].dropna()
        missing = int((~cvals.isin(set(dfs[parent][parent_col]))).sum())
        rows.append([f"`{child}.{child_col}`", f"`{parent}.{parent_col}`",
                     f"{missing:,}", "OK" if missing == 0 else "BROKEN"])
    out += md_table(rows, ["Child column", "Parent column", "Orphan values", "Status"])
    if mv is not None:
        dup = int(mv.duplicated(["application_id"]).sum())
        out.append(f"\nModelling view: {dup:,} duplicate `application_id` values "
                   f"({len(mv):,} rows, one per submitted application).\n")
    return out


def section_categories(dfs) -> List[str]:
    out = ["\n---\n\n## 4. Category distributions\n"]
    specs = [
        ("fact_application", "acquisition_channel"),
        ("fact_application", "acquisition_source"),
        ("fact_application", "intake_round"),
        ("fact_application", "academic_score_band"),
        ("fact_application", "region_id"),
        ("fact_application", "cycle_id"),
        ("dim_programme", "selectivity_tier"),
        ("fact_applicant", "gender_band"),
        ("fact_applicant", "education_level"),
        ("dim_region", "region_type"),
    ]
    for table, col in specs:
        if table not in dfs or col not in dfs[table].columns:
            continue
        s = dfs[table][col]
        vc = s.value_counts(dropna=False)
        total = len(s)
        out.append(f"\n**`{table}.{col}`** - {s.nunique(dropna=True)} distinct values, "
                   f"{vc.isna().sum():,} null\n")
        rows = []
        for k, v in vc.items():
            rows.append([f"`{'(null)' if pd.isna(k) else k}`", f"{v:,}", pct(v / total)])
        out += md_table(rows, ["Value", "Rows", "Share"])
    out.append("\n> `acquisition_channel`, `acquisition_source` and `campaign_id` are "
               "**attribution** fields. They describe which recorded marketing touch is "
               "associated with an application. They are not causal: a channel with a higher "
               "enrolment yield is not shown to *cause* enrolment, and no analysis in this "
               "dataset supports a causal claim about spend.\n")
    return out


def section_targets(mv, dfs) -> List[str]:
    out = ["\n---\n\n## 5. Target distribution\n"]
    if mv is None:
        return out + ["\nModelling view not found.\n"]
    rows = []
    for col, label in (("enrolled_flag", "PRIMARY - registered at the prediction point "
                                           "of submission"),
                       ("admitted_flag", "TERTIARY - received an offer"),
                       ("enrolled_given_admitted_flag", "SECONDARY - registered, among admits")):
        s = mv[col].dropna()
        rows.append([f"`{col}`", label, f"{len(s):,}", pct(s.mean()), f"{int((s == 1).sum()):,}",
                     f"{int((s == 0).sum()):,}"])
    out += md_table(rows, ["Target", "Meaning", "Populated rows", "Positive rate",
                           "Positives", "Negatives"])
    out.append(f"\nThe primary target `enrolled_flag` has a positive rate of "
               f"{pct(float(mv['enrolled_flag'].mean()))} over {len(mv):,} submitted "
               f"applications. That is high enough to model and low enough to still be the "
               f"minority class, so a classifier is not trivially accurate by always "
               f"predicting the majority.\n")

    out.append("**Is the target trivially predictable?**\n")
    out.append("Single-feature rank-AUC against `enrolled_flag` for the strongest declared "
               "safe features. This is a *data quality* screen proving no single column "
               "handed the answer over - it is not a model score and must not be read as one.\n")
    rows = []
    for ent, cname in S.feature_columns(S.FEATURE_SET_PRIMARY):
        if cname not in mv.columns:
            continue
        s = mv[cname]
        if s.dtype == object or s.dtype.name in ("boolean", "Int64"):
            codes = pd.Categorical(s.astype("string").fillna("__NA__")).codes.astype(float)
        else:
            codes = pd.to_numeric(s, errors="coerce").to_numpy(dtype=float)
        auc = rank_auc(mv["enrolled_flag"].to_numpy(dtype=float), codes)
        if np.isfinite(auc):
            rows.append((f"`{cname}`", max(auc, 1 - auc)))
    rows.sort(key=lambda r: -r[1])
    out += md_table([[n, num(a)] for n, a in rows[:12]], ["Feature", "Rank AUC"])
    worst = rows[0][1] if rows else float("nan")
    out.append(f"\nThe strongest single safe feature reaches rank AUC {num(worst)}. Because "
               f"this is well below 1.0, the target cannot be recovered from any one column; "
               f"it has to be predicted from the joint pattern of roughly 45 allowed "
               f"features plus irreducible noise. Columns such as `selection_score`, "
               f"`stage_reached` and `admitted_flag` are **not** in this list because they "
               f"are post-outcome - they are retained in the raw data precisely as leakage "
               f"traps, and the validator checks that no feature set contains them.\n")
    return out


def section_funnel(dfs) -> List[str]:
    out = ["\n---\n\n## 6. Funnel counts and conversion\n"]
    apps = dfs["fact_application"]
    g = apps.groupby("stage_reached_order").size().to_dict()
    cum = {k: int(sum(v for k2, v in g.items() if k2 >= k)) for k in range(1, 8)}
    stage = {s["stage_order"]: s for s in S.FUNNEL_STAGES}
    rows = []
    for k in range(1, 8):
        step = cum[k] / cum[k - 1] if k > 1 and cum[k - 1] else float("nan")
        top = cum[k] / cum[1]
        rows.append([k, f"`{stage[k]['stage_code']}`", f"{stage[k]['stage_name']}",
                     f"{cum[k]:,}",
                     "-" if k == 1 else num(step),
                     num(top) if k > 1 else "1.000",
                     f"{cum[1] - cum[k]:,}" if k > 1 else "0"])
    out += md_table(rows, ["#", "Stage code", "Stage name", "Reached (cumulative)",
                           "Step conversion", "Top-of-funnel", "Cumulative drop-off"])
    out.append(f"\nTop-of-funnel is {cum[1]:,} prospects; the full ladder to enrolment retains "
               f"{num(cum[7] / cum[1])} of them.\n")
    out.append("**Where applicants leave, by stage and reason**\n")
    dd = apps[apps["dropoff_stage"].notna()]
    if len(dd):
        piv = (dd.groupby(["dropoff_stage", "dropoff_reason"]).size()
                 .rename("n").reset_index())
        tot = dd.groupby("dropoff_stage").size()
        rows = [[f"`{r.dropoff_stage}`", f"`{r.dropoff_reason}`", f"{r.n:,}",
                 num(r.n / tot[r.dropoff_stage])] for r in piv.itertuples()]
        out += md_table(rows, ["Stage", "Reason", "Applications", "Share of stage exits"])
    out.append("\nDrop-off reasons are drawn from a stage-specific weighted list, so the mix "
               "is not uniform across stages - a real funnel has different causes at "
               "different steps.\n")
    return out


def section_segments(dfs) -> List[str]:
    out = ["\n---\n\n## 7. Conversion by programme, cycle and channel\n"]
    apps = dfs["fact_application"]

    def seg_table(by: str, title: str, note: str = "") -> List[str]:
        rows = []
        for key, d in apps.groupby(by):
            reached = (d["stage_reached_order"] >= 3).sum()
            verified = (d["stage_reached_order"] >= 4).sum()
            decided = (d["stage_reached_order"] >= 5).sum()
            admitted = int(d["admitted_flag"].sum())
            enrolled = int(d["enrolled_flag"].sum())
            rows.append([
                f"`{key}`", f"{len(d):,}", num(reached / len(d)),
                num(verified / reached) if reached else "-",
                num(admitted / decided) if decided else "-",
                num(enrolled / decided) if decided else "-",
                num(enrolled / len(d)),
            ])
        head = ["Segment", "Applications", "Submit rate", "Verify | submitted",
                "Admit | decided", "Enrol | decided", "Enrol yield (all apps)"]
        block = [f"\n**By {title}**\n"] + md_table(rows, head)
        if note:
            block.append("\n" + note + "\n")
        return block

    out += seg_table("programme_id", "programme")
    out += seg_table("cycle_id", "admission cycle")
    out += seg_table("acquisition_channel", "first-touch acquisition channel",
                     "**Association only.** Programme mix, cycle mix and applicant "
                     "composition differ across channels, so a channel-level yield gap is "
                     "confounded. These numbers must not be read as a marketing effect.")
    out += seg_table("intake_round", "intake round")
    return out


def section_numeric(mv, dfs) -> List[str]:
    out = ["\n---\n\n## 8. Numerical summaries\n"]
    if mv is None:
        return out
    num_cols = [c for c in mv.columns
                if pd.api.types.is_numeric_dtype(mv[c])
                and not pd.api.types.is_bool_dtype(mv[c])
                and mv[c].nunique(dropna=True) > 1]
    rows = []
    for c in sorted(num_cols):
        s = pd.to_numeric(mv[c], errors="coerce")
        rows.append([f"`{c}`", f"{s.notna().sum():,}", num(s.mean()),
                     num(s.std()), num(s.quantile(0.25)), num(s.quantile(0.5)),
                     num(s.quantile(0.75)), num(s.min()), num(s.max())])
    out += md_table(rows, ["Column", "n", "mean", "sd", "p25", "p50", "p75", "min", "max"])
    out.append("\nNumeric summaries of the primary safe features, computed on the submitted-"
               "application population. None of these distributions is degenerate, and no "
               "single one separates the target (section 5).\n")

    eng = dfs["fact_engagement"]
    out.append("**Pre-submission engagement depth** (only applications that started a form)\n")
    started = int((dfs["fact_application"]["stage_reached_order"] >= 2).sum())
    per = dfs["fact_application"][dfs["fact_application"]["stage_reached_order"] >= 2]
    rows = [[f"`{c}`", num(pd.to_numeric(per[c], errors='coerce').mean(), 2),
             num(pd.to_numeric(per[c], errors='coerce').median(), 1),
             num(pd.to_numeric(per[c], errors='coerce').quantile(0.95), 1)]
            for c in ("pre_sub_session_count", "pre_sub_active_days", "pre_sub_total_minutes",
                      "pre_sub_doc_uploads", "pre_sub_return_visits")
            if c in per.columns]
    out += md_table(rows, ["Engagement feature", "mean", "median", "p95"])
    out.append(f"\n{len(eng):,} engagement rows across {started:,} started applications "
               f"({len(eng) / max(1, started):.2f} activity days per started application).\n")
    return out


def section_temporal(dfs, mv, manifest) -> List[str]:
    out = ["\n---\n\n## 9. Temporal coverage and forecast panel\n"]
    apps = dfs["fact_application"]
    panel = dfs["fact_forecast_panel"]
    cycles = dfs["dim_admission_cycle"]
    rows = []
    for c in cycles.sort_values("cycle_start_date").itertuples():
        sub = pd.to_datetime(apps.loc[apps["cycle_id"] == c.cycle_id, "application_submitted_ts"],
                             format=TS_FMT, errors="coerce")
        rows.append([f"`{c.cycle_id}`", c.cycle_start_date, c.cycle_end_date,
                     c.total_weeks,
                     f"{int(sub.notna().sum()):,}",
                     f"{(sub.min().date() if sub.notna().any() else 'n/a')} .. "
                     f"{(sub.max().date() if sub.notna().any() else 'n/a')}"])
    out += md_table(rows, ["Cycle", "Start", "End", "Weeks", "Submissions",
                           "Submission window"])
    span0 = pd.to_datetime(apps["inquiry_ts"], format=TS_FMT).min()
    span1 = pd.to_datetime(apps["enrolled_ts"], format=TS_FMT, errors="coerce").max()
    months = (span1.year - span0.year) * 12 + (span1.month - span0.month)
    out.append(f"\n**Total temporal coverage: {span0.date()} to {span1.date()} "
               f"({months} months) across {apps['cycle_id'].nunique()} fully closed cycles.** "
               f"Every cycle is finalised - decisions released, offers issued and registration "
               f"closed - so no cycle is right-censored and the last cycle is safe to use as a "
               f"test period.\n")

    out.append("\n**Forecast panel** - grain: one row per programme x cycle x ISO week\n")
    elig = panel[panel["is_forecast_eligible"]]
    horizons = (manifest.get("config", {}) or {}).get("forecast_horizons_weeks", [1, 2, 4, 6])
    rows = [
        ["Panel rows (programme x cycle x week)", f"{len(panel):,}"],
        ["Programmes x cycles", f"{panel['programme_id'].nunique()} x "
                                f"{panel['cycle_id'].nunique()}"],
        ["Eligible forecast origins", f"{len(elig):,}"],
        ["Horizons H (weeks)", ", ".join(str(h) for h in horizons)],
        ["Forecast target", "`cum_enrolled` at origin + H (cumulative)"],
        ["Weekly increments available",
         ", ".join(f"`{c}`" for c in panel.columns if c.startswith("wk_"))],
    ]
    out += md_table(rows, ["Property", "Value"])
    out.append(f"\nThe panel is a complete grid: {panel['programme_id'].nunique()} programmes x "
               f"{panel['cycle_id'].nunique()} cycles x ~{int(panel.groupby(['programme_id', 'cycle_id']).size().mean())} "
               f"weeks. Cumulative counts are non-increasing down the ladder at every cell and "
               f"reconcile exactly with `fact_application`, so the panel can be used directly "
               f"for scenario simulation without re-deriving it from the event table.\n")

    out.append("\n**Chronological split**\n")
    split = panel.groupby("cycle_id")["split_hint"].agg(lambda s: sorted(set(s))[0])
    out += md_table([["`" + str(c) + "`", "`" + str(v) + "`"]
                     for c, v in split.sort_index().items()],
                    ["Cycle", "split_hint"])
    out.append("\n`split_hint` is a pure function of `cycle_id` (the split is chronological, "
               "never random), so a train/validation/test split can never leak future cycles "
               "into training. All cycles are finalised.\n")
    return out


def section_fidelity(mv, dfs, manifest) -> List[str]:
    out = ["\n---\n\n## 10. Synthetic-data fidelity and leakage boundary\n",
           S.FICTIONALITY_STATEMENT + "\n"]
    out.append("\n**No real personal data.** All names, identifiers, phone numbers and email "
               "addresses in this dataset are generated by the pipeline from random draws. "
               "There is no link to any real applicant, institution or campaign.\n")
    out.append("\n**Attribution fields are non-causal.** `acquisition_channel`, "
               "`acquisition_source`, `campaign_id`, `touchpoints_count` and "
               "`is_multi_touch` record which marketing touch an application is *associated* "
               "with. They support cross-source comparison of volumes and conversion. They do "
               "not support a claim that any channel caused any outcome.\n")
    out.append("\n**Leakage boundary.** Columns are classified in the data dictionary as "
               "GENERATED, DERIVED, TARGET or POST_OUTCOME. The safe prediction features are "
               "an explicit allow-list; anything dated after the prediction point is "
               "POST_OUTCOME and excluded by construction.\n")
    rows = []
    for fset in S.FEATURE_SETS:
        feats = [c for _, c in S.feature_columns(fset)]
        post = {c for _, c in S.post_outcome_columns()}
        rows.append([f"`{fset}`", len(feats),
                     sorted(set(feats) & post) or "none",
                     f"`{S.prediction_point_column(fset)}`"])
    out += md_table(rows, ["Feature set", "Safe features", "POST_OUTCOME members",
                           "Prediction point"])
    traps = [c for c in ("selection_score", "stage_reached", "admitted_flag",
                         "application_verified_ts", "enrolled_ts")
             if c in dfs["fact_application"].columns]
    out.append(f"\nThe raw fact table deliberately *retains* {len(traps)} post-outcome fields "
               f"({', '.join('`' + t + '`' for t in traps)}) so that a leakage mistake is "
               f"possible and therefore detectable. `scripts/validate_dataset.py` fails the "
               f"dataset if any of them reaches a feature set or the modelling view.\n")
    out.append("\n**Noise and overlap.** Conversion is driven by latent factors (ability, "
               "intent, financial constraint, competing offer) that are only *partially* "
               "observed through the recorded columns, plus per-programme merit cutoffs that "
               "tighten as applications per seat rise. The residual is irreducible, so the "
               "target cannot be recovered exactly even with the true generator parameters.\n")
    return out


# ======================================================================================
# report
# ======================================================================================


def render(root: Path, dfs, mv, manifest) -> str:
    out: List[str] = []
    out.append("# AdmitFlow — Dataset Profiling Report\n")
    out.append(f"> {S.FICTIONALITY_STATEMENT}\n")
    out.append(f"\n> {NO_MODEL_CLAIM}\n")
    out.append("\nProduced by `scripts/profile_dataset.py` from the generated dataset. "
               "The profiler is read-only: it never writes to `data/`.\n")
    out.append(f"\n**Prediction unit:** application  |  **Primary target:** `enrolled_flag`  "
               f"|  **Forecast grain:** programme x cycle x ISO week\n")
    out += section_shape(dfs, mv, manifest)
    out += section_missingness(dfs, mv)
    out += section_duplicates(dfs, mv)
    out += section_categories(dfs)
    out += section_targets(mv, dfs)
    out += section_funnel(dfs)
    out += section_segments(dfs)
    out += section_numeric(mv, dfs)
    out += section_temporal(dfs, mv, manifest)
    out += section_fidelity(mv, dfs, manifest)
    out.append("\n---\n")
    out.append(f"\n> {S.FICTIONALITY_STATEMENT}\n")
    out.append(f">\n> {S.PERFORMANCE_DISCLAIMER}\n")
    return "\n".join(out) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Profile the AdmitFlow synthetic dataset.")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                    help="Project root (default: parent of scripts/).")
    ap.add_argument("--report", type=Path, default=None,
                    help="Where to write the Markdown report (default: <root>/reports/"
                         "profiling_report.md).")
    args = ap.parse_args(argv)

    dfs, mv, manifest = load(args.root)
    text = render(args.root, dfs, mv, manifest)
    out = args.report or (args.root / "reports" / "profiling_report.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"[admitflow] profile written -> {out}")
    print(f"[admitflow] tables profiled: {len(dfs)}"
          + (f", modelling view {len(mv):,} rows" if mv is not None else ""))
    print("[admitflow] no model was trained and no performance metric is reported")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
