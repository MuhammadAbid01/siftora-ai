import base64
from datetime import UTC, datetime, timedelta

import jwt

from app.config import get_settings


def _signing_key(secret: str) -> str | bytes:
    """Mirror app/deps.py's verification-side secret handling exactly: it
    tries to base64-decode the configured secret (Supabase's newer secrets
    are base64) and falls back to the raw string. Tokens must be signed the
    same way they'll be verified.
    """
    try:
        return base64.b64decode(secret)
    except Exception:
        return secret


def make_token(*, sub: str, email: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": sub,
        "email": email,
        "aud": "authenticated",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    return jwt.encode(payload, _signing_key(settings.supabase_jwt_secret), algorithm="HS256")


def auth_header(*, sub: str, email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(sub=sub, email=email)}"}
