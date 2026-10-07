import hashlib
import sqlite3

import pytest

from backend.admitflow import auth


def test_valid_login_returns_token(monkeypatch, tmp_path):
    monkeypatch.setattr(auth, 'AUTH_DB_PATH', tmp_path / 'auth.sqlite3')
    token = auth.authenticate('admin@admitflow.local', 'admin123')
    assert isinstance(token, str)
    assert len(token) > 20


def test_password_and_session_are_stored_as_hashes_and_survive_reinitialization(monkeypatch, tmp_path):
    database_path = tmp_path / 'auth.sqlite3'
    monkeypatch.setattr(auth, 'AUTH_DB_PATH', database_path)
    token = auth.authenticate('admin@admitflow.local', 'admin123')

    with sqlite3.connect(database_path) as connection:
        password_hash, token_hash = connection.execute(
            "SELECT password_hash, (SELECT token_hash FROM sessions) FROM users"
        ).fetchone()
    assert password_hash != b'admin123'
    assert token_hash == hashlib.sha256(token.encode('utf-8')).hexdigest()

    auth.initialize_auth_db()
    assert auth.validate_token(token) == {'sub': 'admin@admitflow.local', 'role': 'admin'}
    assert auth.revoke_token(token)
    with pytest.raises(ValueError):
        auth.validate_token(token)


def test_invalid_login_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(auth, 'AUTH_DB_PATH', tmp_path / 'auth.sqlite3')
    with pytest.raises(ValueError):
        auth.authenticate('bad@example.com', 'wrong')


def test_stateless_production_auth_uses_signed_expiring_tokens(monkeypatch):
    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.setenv('ADMITFLOW_ADMIN_EMAIL', 'admin@example.com')
    monkeypatch.setenv('ADMITFLOW_ADMIN_PASSWORD', 'production-password')
    monkeypatch.setenv('ADMITFLOW_AUTH_SECRET', 'test-signing-secret-long-enough-for-hs256')

    token = auth.authenticate('ADMIN@example.com', 'production-password')

    assert auth.validate_token(token) == {'sub': 'admin@example.com', 'role': 'admin'}
    assert not auth.revoke_token(token)
    with pytest.raises(ValueError):
        auth.authenticate('admin@example.com', 'wrong-password')
    with pytest.raises(ValueError):
        auth.validate_token(f'{token}tampered')
