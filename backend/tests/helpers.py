from datetime import UTC, datetime, timedelta

import jwt

from app.config import get_settings


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
    return jwt.encode(payload, settings.supabase_jwt_secret, algorithm="HS256")


def auth_header(*, sub: str, email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(sub=sub, email=email)}"}
