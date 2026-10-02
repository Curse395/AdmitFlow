# Evidence Package

This directory is the project evidence store for all verified work.

## Evidence rules

- Only include artifacts generated from actual execution.
- Do not fabricate screenshots, metrics, or outputs.
- Every major task must map to one or more evidence artifacts.
- Store all generated outputs under the relevant subdirectory.
- Link evidence in the tracker and verification notes.

## Structure

- `screenshots/` — UI captures and validation images
- `metrics/` — model and analytics metric outputs
- `tests/` — pytest or frontend test output reports
- `models/` — trained model artifacts and metadata
- `reports/` — analysis and summary reports
- `api/` — API request/response recordings and contract checks
- `security/` — auth, authorization, and privacy verification outputs
- `ui/` — UI validation and interaction evidence
- `dataset/` — synthetic dataset validation and profiling outputs

## Required evidence types

- screenshot
- generated report
- test output
- metric output
- artifact path
- verification note

## Evidence policy

If a result has not been executed or verified in the current environment, it must remain marked as `NOT VERIFIED` in the tracker and related documentation.
