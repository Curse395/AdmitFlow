from backend.admitflow.auth import authenticate


def test_valid_login_returns_token():
    token = authenticate('admin@admitflow.local', 'admin123')
    assert isinstance(token, str)
    assert len(token) > 20


def test_invalid_login_raises():
    try:
        authenticate('bad@example.com', 'wrong')
        assert False
    except ValueError:
        assert True
