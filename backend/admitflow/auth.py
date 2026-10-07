from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import logging
import os
import secrets
import socket
import sqlite3
from collections.abc import Iterator
from typing import Any
from urllib.parse import unquote, urlsplit

import jwt

from .config import AUTH_DB_PATH, DEMO_USER_EMAIL, DEMO_USER_PASSWORD

PASSWORD_HASH_ITERATIONS = 310_000
SESSION_TTL = timedelta(hours=8)
logger = logging.getLogger(__name__)


def _uses_stateless_auth() -> bool:
    return bool(os.getenv("VERCEL")) and not os.getenv("DATABASE_URL")


def _auth_signing_key() -> str:
    key = os.getenv("ADMITFLOW_AUTH_SECRET")
    if not key:
        raise RuntimeError("ADMITFLOW_AUTH_SECRET is required for stateless production auth.")
    return key


def _safe_database_error(error: Exception, database_url: str) -> str:
    message = str(error).replace(database_url, "<redacted DATABASE_URL>")
    try:
        password = urlsplit(database_url).password
    except ValueError:
        password = None
    if password:
        message = message.replace(password, "<redacted>").replace(unquote(password), "<redacted>")
    return message[:300]


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        import psycopg
        from psycopg.rows import dict_row

        try:
            connection_options = {}
            if os.getenv("VERCEL"):
                database = urlsplit(database_url)
                addresses = socket.getaddrinfo(
                    database.hostname,
                    database.port or 5432,
                    family=socket.AF_INET,
                    type=socket.SOCK_STREAM,
                )
                connection_options["hostaddr"] = addresses[0][4][0]
            with psycopg.connect(database_url, row_factory=dict_row, **connection_options) as connection:
                yield connection
        except Exception as exc:
            logger.error(
                "PostgreSQL auth storage error (%s, SQLSTATE=%s): %s",
                type(exc).__name__,
                getattr(exc, "sqlstate", None),
                _safe_database_error(exc, database_url),
            )
            raise
        return

    AUTH_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(AUTH_DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def _execute(connection: Any, statement: str, parameters: tuple = ()) -> Any:
    if os.getenv("DATABASE_URL"):
        statement = statement.replace("?", "%s")
    return connection.execute(statement, parameters)


def _password_hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS)


def initialize_auth_db() -> None:
    if _uses_stateless_auth():
        if not os.getenv("ADMITFLOW_ADMIN_EMAIL") or not os.getenv("ADMITFLOW_ADMIN_PASSWORD"):
            raise RuntimeError("Production admin credentials are not configured.")
        _auth_signing_key()
        return

    postgres = bool(os.getenv("DATABASE_URL"))
    with _connection() as connection:
        binary_type = "BYTEA" if postgres else "BLOB"
        _execute(
            connection,
            f"""CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                password_salt {binary_type} NOT NULL,
                password_hash {binary_type} NOT NULL,
                created_at TEXT NOT NULL
            )""",
        )
        _execute(
            connection,
            """CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                email TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                expires_at INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        email = os.getenv("ADMITFLOW_ADMIN_EMAIL", "").strip().lower() if postgres else DEMO_USER_EMAIL
        password = os.getenv("ADMITFLOW_ADMIN_PASSWORD") if postgres else DEMO_USER_PASSWORD
        if not email or not password:
            raise RuntimeError("ADMITFLOW_ADMIN_EMAIL and ADMITFLOW_ADMIN_PASSWORD are required with DATABASE_URL.")
        admin_user = _execute(connection, "SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
        if admin_user is None:
            salt = secrets.token_bytes(16)
            insert = """INSERT INTO users
                   (email, role, password_salt, password_hash, created_at)
                   VALUES (?, 'admin', ?, ?, ?)"""
            if not postgres:
                insert = insert.replace("INSERT INTO", "INSERT OR IGNORE INTO")
            _execute(
                connection,
                insert,
                (email, salt, _password_hash(password, salt), datetime.now(timezone.utc).isoformat()),
            )
        _execute(
            connection,
            "DELETE FROM sessions WHERE expires_at <= ?",
            (int(datetime.now(timezone.utc).timestamp()),),
        )


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_token(email: str, role: str = "admin") -> str:
    if _uses_stateless_auth():
        now = datetime.now(timezone.utc)
        return jwt.encode(
            {
                "sub": email.strip().lower(),
                "role": role,
                "iat": now,
                "exp": now + SESSION_TTL,
            },
            _auth_signing_key(),
            algorithm="HS256",
        )

    initialize_auth_db()
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    with _connection() as connection:
        _execute(
            connection,
            "INSERT INTO sessions (token_hash, email, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (
                _token_hash(token),
                email.strip().lower(),
                int((now + SESSION_TTL).timestamp()),
                now.isoformat(),
            ),
        )
    return token


def validate_token(token: str) -> dict[str, Any]:
    if _uses_stateless_auth():
        try:
            payload = jwt.decode(
                token,
                _auth_signing_key(),
                algorithms=["HS256"],
                options={"require": ["sub", "role", "exp"]},
            )
        except jwt.InvalidTokenError as exc:
            raise ValueError("Invalid or expired token.") from exc
        return {"sub": payload["sub"], "role": payload["role"]}

    initialize_auth_db()
    with _connection() as connection:
        row = _execute(
            connection,
            """SELECT users.email, users.role FROM sessions
               JOIN users ON users.email = sessions.email
               WHERE sessions.token_hash = ? AND sessions.expires_at > ?""",
            (_token_hash(token), int(datetime.now(timezone.utc).timestamp())),
        ).fetchone()
    if row is None:
        raise ValueError("Invalid or expired token.")
    return {"sub": row["email"], "role": row["role"]}


def revoke_token(token: str) -> bool:
    if _uses_stateless_auth():
        return False

    initialize_auth_db()
    with _connection() as connection:
        cursor = _execute(connection, "DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
        return cursor.rowcount > 0


def authenticate(email: str, password: str) -> str:
    if _uses_stateless_auth():
        expected_email = os.getenv("ADMITFLOW_ADMIN_EMAIL", "").strip().lower()
        expected_password = os.getenv("ADMITFLOW_ADMIN_PASSWORD", "")
        if email.strip().lower() != expected_email or not hmac.compare_digest(
            password.encode("utf-8"), expected_password.encode("utf-8")
        ):
            _password_hash(password, bytes(16))
            raise ValueError("Invalid email or password.")
        return create_token(expected_email, "admin")

    initialize_auth_db()
    normalized_email = email.strip().lower()
    with _connection() as connection:
        user = _execute(
            connection,
            "SELECT role, password_salt, password_hash FROM users WHERE email = ?",
            (normalized_email,),
        ).fetchone()
    if user is None:
        _password_hash(password, bytes(16))
        raise ValueError("Invalid email or password.")
    candidate_hash = _password_hash(password, user["password_salt"])
    if not hmac.compare_digest(candidate_hash, user["password_hash"]):
        raise ValueError("Invalid email or password.")
    return create_token(normalized_email, user["role"])


def oauth_configured() -> bool:
    return False
