from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment


WORKBOOK_PATH = "TRACKER.xlsx"


def apply_header(ws, columns):
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)

    for idx, col in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=idx, value=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    ws.freeze_panes = "A2"


wb = Workbook()

# Sheet 1: Master Checklist
master = wb.active
master.title = "Master Checklist"
master_columns = [
    "Task ID",
    "Phase",
    "Task",
    "Requirement",
    "Planned Hours",
    "Owner",
    "Status",
    "Completed Date",
    "Actual Hours",
    "Evidence",
    "Notes",
]
apply_header(master, master_columns)

master_rows = [
    ["A1", "Foundation", "Create project specification", "Project docs and scope", 4, "Project Agent", "Completed", "", "", "docs/PROJECT_SPEC.md", "Initial project scope defined."],
    ["A2", "Foundation", "Create architecture blueprint", "System design and stack", 4, "Project Agent", "Completed", "", "", "docs/ARCHITECTURE.md", "Core architecture documented."],
    ["A3", "Foundation", "Create development plan", "Execution plan", 3, "Project Agent", "Completed", "", "", "docs/DEVELOPMENT_PLAN.md", "Milestones defined."],
    ["A4", "Foundation", "Create acceptance criteria", "Evidence-based completion gates", 3, "Project Agent", "Completed", "", "", "docs/ACCEPTANCE_CRITERIA.md", "Verification criteria established."],
    ["A5", "Foundation", "Initialize evidence structure", "Evidence registry", 2, "Project Agent", "Completed", "", "", "evidence/README.md", "Evidence policy documented."],
    ["A6", "Foundation", "Create Git repository", "Source control", 1, "Project Agent", "In Progress", "", "", "", "Git repository will be initialized during setup."],
    ["A7", "Dataset", "Generate synthetic dataset", "Dataset generation and validation", 12, "Data Science Agent", "Not Started", "", "", "", "Dataset work begins after foundation verification."],
    ["A8", "Analytics", "Build funnel analytics", "Funnel metrics and conversion analysis", 8, "Data Science Agent", "Not Started", "", "", "", "Requires generated dataset."],
    ["A9", "Analytics", "Build cohort analytics", "Cohort and segment analysis", 8, "Data Science Agent", "Not Started", "", "", "", "Requires validated dataset."],
    ["A10", "Analytics", "Implement attribution", "Descriptive attribution analysis", 6, "Data Science Agent", "Not Started", "", "", "", "Must avoid causal claims."],
    ["A11", "ML", "Train baseline and advanced models", "Model training and comparison", 12, "ML Agent", "Not Started", "", "", "", "Model metrics to be captured from execution."],
    ["A12", "Forecasting", "Build forecast pipeline", "H1/H2/H4/H6 forecast evaluation", 10, "Data Science Agent", "Not Started", "", "", "", "Temporal leakage checks required."],
    ["A13", "Simulation", "Build scenario engine", "Deterministic scenario lab", 8, "Analytics Agent", "Not Started", "", "", "", "Scenario outputs must be deterministic."],
    ["A14", "Backend", "Implement FastAPI backend", "API and backend services", 12, "Backend Agent", "Not Started", "", "", "", "Includes auth and audit flows."],
    ["A15", "Frontend", "Build analytics frontend", "UI, dashboard, and charts", 14, "Frontend Agent", "Not Started", "", "", "", "Must include light/dark theme."],
    ["A16", "Testing", "Run full verification suite", "Unit, integration, failures, security, and UI", 10, "QA Agent", "Not Started", "", "", "", "Evidence required before final verification."],
    ["A17", "Documentation", "Prepare final project report", "Final project summary and verification", 4, "Project Agent", "Not Started", "", "", "", "Final evidence must be linked."],
]
for row in master_rows:
    master.append(row)

# Sheet 2: Work Log
work_log = wb.create_sheet("Work Log")
work_columns = ["Date", "Task ID", "Owner", "Activity", "Actual Hours", "Evidence", "Outcome"]
apply_header(work_log, work_columns)

# Sheet 3: Evidence Register
register = wb.create_sheet("Evidence Register")
register_columns = ["Evidence ID", "Date", "Task ID", "Evidence Type", "Description", "File Path", "Result", "Verified By", "Notes"]
apply_header(register, register_columns)

# Sheet 4: Test Register
tests = wb.create_sheet("Test Register")
test_columns = ["Test ID", "Task ID", "Test", "Command", "Expected", "Actual", "Status", "Evidence"]
apply_header(tests, test_columns)

# Sheet 5: Model Results
models = wb.create_sheet("Model Results")
model_columns = ["Model", "Dataset", "Target", "Metrics", "Run Date", "Artifact", "Status"]
apply_header(models, model_columns)

# Sheet 6: Dashboard
summary = wb.create_sheet("Dashboard")
summary_columns = ["Metric", "Value"]
apply_header(summary, summary_columns)
summary.append(["total tasks", 17])
summary.append(["completed", 5])
summary.append(["in progress", 1])
summary.append(["blocked", 0])
summary.append(["not started", 11])
summary.append(["total planned hours", 123])
summary.append(["total recorded actual hours", ""])
summary.append(["evidence count", 0])
summary.append(["test pass count", 0])
summary.append(["test failure count", 0])

# Auto-size columns
for ws in wb.worksheets:
    for column_cells in ws.columns:
        max_length = 0
        column = column_cells[0].column_letter
        for cell in column_cells:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except Exception:
                pass
        adjusted_width = max(10, max_length + 2)
        ws.column_dimensions[column].width = adjusted_width

wb.save(WORKBOOK_PATH)
print(f"Created {WORKBOOK_PATH} with required sheets and tracker structure.")
