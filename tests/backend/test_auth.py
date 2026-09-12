import logging
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from app.auth.security import AUDIENCE, COOKIE_NAME, ISSUER
from app.database import get_session
from app.models import Role, User
from conftest import CSRF, TEST_PASSWORD
from sqlalchemy import select
from sqlalchemy.exc import OperationalError


def test_health_includes_runtime_metadata(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "auladata-api",
        "environment": "TEST",
        "version": "v1.0.0-test",
        "commit": "test-commit",
    }


def test_ready_checks_database(client):
    assert client.get("/ready").json() == {"status": "ok", "database": "ok"}


def test_login_admin_creates_http_only_secure_cookie(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "  ADMIN@EXAMPLE.COM  ", "password": TEST_PASSWORD},
        headers=CSRF,
    )
    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"
    assert set(response.json()) == {"id", "name", "email", "role", "is_active"}
    cookie = response.headers["set-cookie"].lower()
    assert all(flag in cookie for flag in ["httponly", "secure", "samesite=lax", "path=/"])
    assert "password" not in response.text
    assert "token" not in response.text


@pytest.mark.parametrize(
    "email,password",
    [
        ("admin@example.com", "incorrect-password"),
        ("missing@example.com", TEST_PASSWORD),
        ("inactive@example.com", TEST_PASSWORD),
    ],
)
def test_invalid_login_is_rejected_without_user_disclosure(client, email, password):
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}, headers=CSRF
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Correo o contraseña incorrectos"
    assert "set-cookie" not in response.headers


def test_auth_me_returns_current_user(admin_client):
    response = admin_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "admin@example.com"
    assert response.headers["cache-control"] == "no-store"


def test_logout_clears_cookie_and_session(admin_client):
    response = admin_client.post("/api/v1/auth/logout", headers=CSRF)
    assert response.status_code == 204
    assert response.content == b""
    assert admin_client.get("/api/v1/auth/me").status_code == 401


@pytest.mark.parametrize("path", ["/api/v1/auth/me", "/api/v1/classrooms", "/api/v1/classrooms/1"])
def test_unauthenticated_get_is_rejected(client, path):
    assert client.get(path).status_code == 401


def test_expired_token_is_rejected(client, application):
    settings = application.state.settings
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "1",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
            "iss": ISSUER,
            "aud": AUDIENCE,
        },
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    client.cookies.set(COOKIE_NAME, token)
    assert client.get("/api/v1/auth/me").status_code == 401


def test_tampered_token_is_rejected(client):
    client.cookies.set(COOKIE_NAME, "invalid.jwt.signature")
    assert client.get("/api/v1/auth/me").status_code == 401


def test_deactivated_user_session_is_rejected(admin_client, application):
    with application.state.session_factory() as session:
        user = session.scalar(select(User).where(User.email == "admin@example.com"))
        user.is_active = False
        session.commit()
    assert admin_client.get("/api/v1/auth/me").status_code == 401


def test_role_changes_take_effect_without_new_token(admin_client, application, classroom_payload):
    with application.state.session_factory() as session:
        user = session.scalar(select(User).where(User.email == "admin@example.com"))
        user.role = Role.VIEWER
        session.commit()
    response = admin_client.post("/api/v1/classrooms", json=classroom_payload, headers=CSRF)
    assert response.status_code == 403


@pytest.mark.parametrize(
    "headers", [{}, {"X-Requested-With": "AulaData", "Origin": "https://evil.example"}]
)
def test_login_requires_csrf_protection(client, headers):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": TEST_PASSWORD},
        headers=headers,
    )
    assert response.status_code == 403


def test_cors_does_not_allow_untrusted_origins(client):
    response = client.options(
        "/api/v1/classrooms",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Requested-With",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_readiness_failure_preserves_liveness(client, application, monkeypatch):
    def unavailable():
        raise OperationalError("private SQL", {}, Exception("private database credential"))

    monkeypatch.setattr(application.state.engine, "connect", unavailable)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unavailable"}
    assert client.get("/health").status_code == 200


def test_database_errors_do_not_expose_secrets(client, application):
    def unavailable_session():
        raise OperationalError("private SQL", {}, Exception("private database credential"))

    application.dependency_overrides[get_session] = unavailable_session
    response = client.get("/api/v1/classrooms")
    assert response.status_code == 503
    assert response.json() == {"detail": "Base de datos no disponible"}
    assert "private" not in response.text


@pytest.mark.parametrize("kind", ["password_too_long", "extra_token", "invalid_body"])
def test_validation_errors_do_not_echo_secrets(client, caplog, monkeypatch, kind):
    secret = "sensitive-input-marker-" * 8
    payload = {"email": "admin@example.com", "password": secret}
    if kind == "extra_token":
        payload = {"email": "admin@example.com", "password": TEST_PASSWORD, "token": secret}
    elif kind == "invalid_body":
        payload = [{"password": secret}]
    monkeypatch.setattr(logging.getLogger("auladata"), "propagate", True)
    response = client.post("/api/v1/auth/login", json=payload, headers=CSRF)
    assert response.status_code == 422
    assert secret not in response.text
    assert all(set(error) == {"type", "loc", "msg"} for error in response.json()["detail"])
    assert "request_failed" in caplog.text
    assert secret not in caplog.text
