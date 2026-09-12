"""Disposable SQLite tests; TEST_DATABASE_URL opts into an isolated PostgreSQL schema."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

# Importing the ASGI entrypoint must never read a developer's database configuration.
os.environ["APP_ENV"] = "TEST"
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET"] = "isolated-tests-only-never-deploy-this-key"
os.environ["CORS_ORIGINS"] = "https://testserver"
os.environ["ADMIN_INITIAL_EMAIL"] = "admin@example.com"
os.environ["VIEWER_INITIAL_EMAIL"] = "viewer@example.com"

from app.auth.security import hash_password  # noqa: E402
from app.config import Settings, get_settings  # noqa: E402
from app.database import Base  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Role, User  # noqa: E402
from app.schemas.classroom import ClassroomCreate  # noqa: E402
from app.services.classrooms import create_classroom  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TEST_PASSWORD = "Isolated-test-password-2026"
CSRF = {"X-Requested-With": "AulaData", "Origin": "https://testserver"}


@pytest.fixture(scope="session")
def database_url():
    target = os.environ.get("TEST_DATABASE_URL")
    if not target:
        yield "sqlite+pysqlite:///:memory:"
        return
    parsed = make_url(target)
    if parsed.drivername != "postgresql+psycopg" or "test" not in (parsed.database or "").lower():
        raise RuntimeError(
            "TEST_DATABASE_URL debe usar PostgreSQL y una BD cuyo nombre incluya test"
        )
    schema = f"auladata_test_{uuid4().hex}"
    administrative_engine = create_engine(parsed)
    with administrative_engine.begin() as connection:
        # The identifier is generated internally and contains only [a-z0-9_].
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    isolated_url = parsed.update_query_dict({"options": f"-csearch_path={schema}"})
    isolated_target = isolated_url.render_as_string(hide_password=False)
    previous = os.environ["DATABASE_URL"]
    try:
        os.environ["DATABASE_URL"] = isolated_target
        get_settings.cache_clear()
        command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
        command.check(Config(str(ROOT / "alembic.ini")))
        yield isolated_target
    finally:
        os.environ["DATABASE_URL"] = previous
        get_settings.cache_clear()
        with administrative_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        administrative_engine.dispose()


@pytest.fixture(scope="session")
def password_hash():
    return hash_password(TEST_PASSWORD)


@pytest.fixture
def application(database_url, password_hash):
    settings = Settings(
        _env_file=None,
        app_env="TEST",
        testing=True,
        database_url=database_url,
        jwt_secret="isolated-tests-only-never-deploy-this-key",
        cookie_secure=True,
        cors_origins="https://testserver",
        app_version="v1.0.0-test",
        git_commit="test-commit",
        admin_initial_email=None,
        admin_initial_password=None,
        viewer_initial_email=None,
        viewer_initial_password=None,
        seed_demo=False,
    )
    app = create_app(settings)
    engine = app.state.engine
    if database_url.startswith("sqlite"):
        Base.metadata.create_all(engine)
    connection = engine.connect()
    transaction = connection.begin()
    if database_url.startswith("sqlite"):
        # Python's legacy SQLite transaction mode does not BEGIN before a SAVEPOINT.
        connection.exec_driver_sql("BEGIN")
    app.state.session_factory = sessionmaker(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    with app.state.session_factory() as session:
        session.add_all(
            [
                User(
                    name="Admin",
                    email="admin@example.com",
                    password_hash=password_hash,
                    role=Role.ADMIN,
                    is_active=True,
                ),
                User(
                    name="Viewer",
                    email="viewer@example.com",
                    password_hash=password_hash,
                    role=Role.VIEWER,
                    is_active=True,
                ),
                User(
                    name="Inactive",
                    email="inactive@example.com",
                    password_hash=password_hash,
                    role=Role.ADMIN,
                    is_active=False,
                ),
            ]
        )
        session.commit()
    with TestClient(app, base_url="https://testserver") as http:
        app.state.test_client = http
        try:
            yield app
        finally:
            # Roll back before lifespan closes the SQLite StaticPool connection.
            transaction.rollback()
            connection.close()


@pytest.fixture
def client(application):
    return application.state.test_client


@pytest.fixture
def admin_client(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": TEST_PASSWORD},
        headers=CSRF,
    )
    assert response.status_code == 200
    return client


@pytest.fixture
def viewer_client(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@example.com", "password": TEST_PASSWORD},
        headers=CSRF,
    )
    assert response.status_code == 200
    return client


@pytest.fixture
def classroom_payload():
    return {
        "clave": "ISC-A01",
        "nombre": "Laboratorio de Redes",
        "edificio": "Edificio K",
        "capacidad": 30,
        "tipo": "LABORATORIO",
        "estado": "ACTIVA",
    }


@pytest.fixture
def classroom_id(application, classroom_payload):
    with application.state.session_factory() as session:
        classroom = create_classroom(session, ClassroomCreate(**classroom_payload))
        return classroom.id
