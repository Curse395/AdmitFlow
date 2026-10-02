from __future__ import annotations

from pathlib import Path
import json

from backend.admitflow.data_generator import generate_admission_dataset, save_validation_report
from backend.admitflow.analytics import dashboard_metrics, funnel_overview, programme_comparison

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "admission_data.csv"
REPORT_PATH = ROOT / "data" / "validation_report.json"
SUMMARY_PATH = ROOT / "evidence" / "dataset" / "dataset_summary.json"


def main() -> None:
    df = generate_admission_dataset(DATASET_PATH, rows=4200, seed=42)
    report = save_validation_report(df, REPORT_PATH)
    dashboard = dashboard_metrics(df)
    funnel = funnel_overview(df)
    programmes = programme_comparison(df).to_dict(orient="records")
    summary = {
        "rows": int(len(df)),
        "report": report,
        "dashboard": dashboard,
        "funnel": funnel,
        "programme_comparison": programmes,
    }
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Dataset saved to {DATASET_PATH}")
    print(f"Validation report saved to {REPORT_PATH}")
    print(f"Summary saved to {SUMMARY_PATH}")
    print(report)


if __name__ == "__main__":
    main()
