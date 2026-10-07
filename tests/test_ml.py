import pandas as pd

from backend.admitflow.ml import train_model


def test_models_report_metrics_and_top_features(tmp_path):
    df = pd.read_csv('data/admission_data.csv')
    metrics = train_model(df, artifact_path=tmp_path / 'models.joblib')

    for model_name in ('baseline', 'advanced'):
        result = metrics[model_name]
        assert {'log_loss', 'roc_auc', 'pr_auc', 'accuracy', 'precision', 'recall', 'f1', 'confusion_matrix'} <= result.keys()
        assert len(result['top_features']) == 10
        assert all(feature['feature'] for feature in result['top_features'])


def test_models_accept_nullable_string_dtype_categories(tmp_path):
    df = pd.read_csv('data/admission_data.csv')
    categorical = ['programme', 'selectivity', 'region', 'campaign_source']
    df[categorical] = df[categorical].astype('string')

    metrics = train_model(df, artifact_path=tmp_path / 'models.joblib')

    assert {'baseline', 'advanced'} <= metrics.keys()
