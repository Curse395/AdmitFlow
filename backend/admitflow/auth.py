from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from .config import DEMO_USER_EMAIL, DEMO_USER_PASSWORD, JWT_SECRET


def create_token(email: str, role: str = "admin") -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=8)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def validate_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    return payload


def authenticate(email: str, password: str) -> str:
    if email == DEMO_USER_EMAIL and password == DEMO_USER_PASSWORD:
        return create_token(email)
    raise ValueError("Invalid email or password.")


def oauth_configured() -> bool:
    return False
