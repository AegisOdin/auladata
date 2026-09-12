import logging
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import Settings

COOKIE_NAME = "auladata_session"
ISSUER = "auladata-api"
AUDIENCE = "auladata-browser"
logger = logging.getLogger("auladata.auth")
password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
# Unknown accounts still perform an Argon2 verification to reduce timing disclosure.
_dummy_hash = password_hasher.hash(token_urlsafe(32))


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        result = password_hasher.verify(password_hash or _dummy_hash, password)
        return bool(result and password_hash)
    except (VerificationError, InvalidHashError):
        return False


def create_token(user_id: int, settings: Settings) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.jwt_expires_minutes),
            "iss": ISSUER,
            "aud": AUDIENCE,
        },
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def read_token(token: str, settings: Settings) -> int | None:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={"require": ["sub", "iat", "exp", "iss", "aud"]},
        )
        user_id = int(payload["sub"])
        return user_id if user_id > 0 else None
    except (jwt.InvalidTokenError, TypeError, ValueError, KeyError) as exc:
        logger.warning("session_rejected reason=%s", type(exc).__name__)
        return None
