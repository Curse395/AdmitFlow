import pandas as pd
import pytest

from backend.admitflow.scenario import scenario_engine


def test_scenario_returns_expected_keys():
    df = pd.read_csv('data/admission_data.csv')
    result = scenario_engine(df, application_volume=5200, stage_adjustments={'submitted': 1.1, 'admitted': 1.15, 'enrolled': 1.08})
    assert 'baseline' in result
    assert 'scenario' in result
    assert 'difference' in result
    assert 'percentage_change' in result
    assert result['deterministic'] is True


def test_scenario_scales_stage_counts_with_application_volume():
    df = pd.read_csv('data/admission_data.csv')
    baseline_volume = len(df)
    result = scenario_engine(
        df,
        application_volume=baseline_volume * 2,
        stage_adjustments={'submitted': 1, 'admitted': 1, 'enrolled': 1},
        campaign_shift={},
    )

    assert result['scenario']['submitted'] == result['baseline']['submitted'] * 2
    assert result['scenario']['admitted'] == result['baseline']['admitted'] * 2
    assert result['scenario']['enrolled'] == result['baseline']['enrolled'] * 2
    assert result['scenario']['applications'] >= result['scenario']['submitted'] >= result['scenario']['admitted'] >= result['scenario']['enrolled']


def test_scenario_rejects_negative_application_volume():
    df = pd.read_csv('data/admission_data.csv')
    with pytest.raises(ValueError, match='non-negative'):
        scenario_engine(df, application_volume=-1)
