from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select

from app.auth.security import COOKIE_NAME, create_token, verify_password
from app.dependencies.auth import CurrentUser, DatabaseSession, verify_csrf
from app.models import User
from app.schemas.auth import LoginRequest, UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])


@router.post(
    "/login",
    response_model=UserResponse,
    dependencies=[Depends(verify_csrf)],
    responses={
        401: {"description": "Credenciales inválidas"},
        403: {"description": "Origen inválido"},
    },
)
def login(payload: LoginRequest, request: Request, response: Response, session: DatabaseSession):
    user = session.scalar(select(User).where(User.email == str(payload.email)))
    password_valid = verify_password(payload.password, user.password_hash if user else None)
    if not user or not password_valid or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos")
    settings = request.app.state.settings
    response.set_cookie(
        COOKIE_NAME,
        create_token(user.id, settings),
        max_age=settings.jwt_expires_minutes * 60,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return user


@router.post("/logout", status_code=204, dependencies=[Depends(verify_csrf)])
def logout(request: Request):
    response = Response(status_code=204)
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        secure=request.app.state.settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/me", response_model=UserResponse, responses={401: {"description": "Sin sesión"}})
def current_user(user: CurrentUser):
    return user
