import pandas as pd

from backend.admitflow.data_generator import validate_dataset


def test_dataset_is_valid():
    df = pd.read_csv('data/admission_data.csv')
    report = validate_dataset(df)
    assert report['is_valid'] is True
    assert report['duplicates'] == 0
    assert report['invalid_dates'] == 0
