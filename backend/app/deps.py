from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel

from app.config import Settings, get_settings


class CurrentUser(BaseModel):
    id: str
    email: str


def _unauthorized(message: str = "Not authenticated") -> HTTPException:
    return HTTPException(status_code=401, detail={"code": "unauthorized", "message": message})


async def get_current_user(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthorized()

    token = authorization.removeprefix("Bearer ")

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid or expired token") from None

    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id or not email:
        raise _unauthorized("Token missing required claims")

    return CurrentUser(id=user_id, email=email)
