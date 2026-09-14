import contextlib
import json
import logging
import urllib.request
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException
from jwt.algorithms import ECAlgorithm, RSAAlgorithm
from pydantic import BaseModel

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class CurrentUser(BaseModel):
    id: str
    email: str


def _unauthorized(message: str = "Not authenticated") -> HTTPException:
    return HTTPException(status_code=401, detail={"code": "unauthorized", "message": message})


@lru_cache(maxsize=1)
def _fetch_jwks(supabase_url: str) -> list[dict]:
    """Fetch and cache public keys from Supabase JWKS endpoint."""
    url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read())
    return data.get("keys", [])


def _get_public_key(supabase_url: str, kid: str | None, alg: str):
    """Return the matching public key from the JWKS, or None if not found."""
    try:
        keys = _fetch_jwks(supabase_url)
    except Exception as e:
        logger.warning("Could not fetch JWKS: %s", e)
        return None

    for key_data in keys:
        if kid and key_data.get("kid") != kid:
            continue
        kty = key_data.get("kty", "")
        try:
            if kty == "EC":
                return ECAlgorithm.from_jwk(key_data)
            if kty == "RSA":
                return RSAAlgorithm.from_jwk(key_data)
        except Exception as e:
            logger.warning("Could not parse JWK: %s", e)
    return None


async def get_current_user(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthorized()

    token = authorization.removeprefix("Bearer ")

    # Decode header without verification to detect algorithm
    try:
        import base64

        header_b64 = token.split(".")[0]
        header_b64 += "=" * (4 - len(header_b64) % 4)
        header = json.loads(base64.b64decode(header_b64))
        alg: str = header.get("alg", "HS256")
        kid: str | None = header.get("kid")
    except Exception:
        raise _unauthorized("Malformed token") from None

    try:
        if alg in ("ES256", "ES384", "ES512", "RS256", "RS384", "RS512"):
            # Asymmetric token — verify with public key from JWKS
            supabase_url = str(settings.supabase_url).rstrip("/")
            public_key = _get_public_key(supabase_url, kid, alg)
            if public_key is None:
                raise _unauthorized("Could not resolve JWT public key")
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[alg],
                audience="authenticated",
            )
        else:
            # Symmetric token — verify with the configured JWT secret
            import base64 as _b64

            secret: str | bytes = settings.supabase_jwt_secret
            with contextlib.suppress(Exception):
                secret = _b64.b64decode(secret)
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256", "HS384", "HS512"],
                audience="authenticated",
            )
    except HTTPException:
        raise
    except jwt.InvalidTokenError as e:
        logger.warning("JWT verification failed: %s", e)
        raise _unauthorized("Invalid or expired token") from None

    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id or not email:
        raise _unauthorized("Token missing required claims")

    return CurrentUser(id=user_id, email=email)
