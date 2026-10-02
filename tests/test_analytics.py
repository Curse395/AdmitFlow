import json

import pandas as pd

from backend.admitflow.analytics import attribution_summary, cycle_comparison, stage_summary


def test_stage_summary_shape():
    df = pd.read_csv('data/admission_data.csv')
    summary = stage_summary(df)
    assert list(summary['stage']) == ['lead', 'application', 'submitted', 'review', 'admitted', 'enrolled']
    assert summary['volume'].iloc[0] == len(df)
    assert summary['volume'].is_monotonic_decreasing
    assert summary['volume'].iloc[-1] == df['enrolled'].sum()
    assert summary['from_previous_stage'].iloc[0] is None
    assert summary['conversion_to_next'].iloc[-1] is None
    json.dumps(summary.to_dict(orient='records'), allow_nan=False)


def test_cycle_comparison_works():
    df = pd.read_csv('data/admission_data.csv')
    result = cycle_comparison(df)
    assert 'cycle_year' in result.columns
    assert len(result) >= 1
