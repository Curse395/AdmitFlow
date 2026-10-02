from backend.admitflow.auth import authenticate, validate_token


def test_token_round_trip():
    token = authenticate('admin@admitflow.local', 'admin123')
    payload = validate_token(token)
    assert payload['sub'] == 'admin@admitflow.local'
    assert payload['role'] == 'admin'


def test_invalid_password_rejected():
    try:
        authenticate('admin@admitflow.local', 'bad-password')
        assert False
    except ValueError:
        assert True
