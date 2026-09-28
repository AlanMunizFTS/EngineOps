from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from ops_platform.core.config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    """Returns the token subject (user email). Raises jwt.PyJWTError if invalid/expired."""
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    return payload["sub"]


DEFAULT_LOGIN_DOMAIN = "martinrea.com"


def normalize_login_identifier(identifier: str, default_domain: str = DEFAULT_LOGIN_DOMAIN) -> str:
    """Lets users log in with just the part before the @ - "jdoe" resolves
    to "jdoe@martinrea.com". An identifier that already contains an "@" is
    used as-is, so accounts on other domains (test/seed accounts, etc.)
    still log in with their full email unchanged."""
    identifier = identifier.strip()
    if "@" in identifier:
        return identifier
    return f"{identifier}@{default_domain}"
