from typing import Annotated

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session

from app.auth.security import COOKIE_NAME, read_token
from app.database import get_session
from app.models import Role, User

session_cookie = APIKeyCookie(name=COOKIE_NAME, auto_error=False, scheme_name="Sesión HttpOnly")
DatabaseSession = Annotated[Session, Depends(get_session)]


def verify_csrf(request: Request) -> None:
    """Require a non-simple request and, when present, an explicitly trusted Origin."""
    if request.headers.get("x-requested-with") != "AulaData":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Se requiere X-Requested-With: AulaData")
    origin = request.headers.get("origin")
    if origin is not None and origin not in request.app.state.settings.allowed_origins:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Origen no permitido")


def get_current_user(
    request: Request,
    session: DatabaseSession,
    cookie: Annotated[str | None, Security(session_cookie)],
) -> User:
    user_id = read_token(cookie, request.app.state.settings) if cookie else None
    user = session.get(User, user_id) if user_id is not None else None
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión inválida o expirada")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != Role.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Se requiere el rol ADMIN")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
