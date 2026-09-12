from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.auth.security import verify_password
from app.config import Settings, get_settings
from app.models import Classroom, User
from app.seed import DEMO_CLASSROOMS, seed_database
from pydantic import ValidationError
from sqlalchemy import create_engine, func, inspect, select


@pytest.mark.parametrize(
    "overrides",
    [
        {"jwt_secret": "short"},
        {
            "app_env": "PROD",
            "testing": False,
            "cookie_secure": False,
            "database_url": "postgresql+psycopg://localhost/auladata",
        },
        {"app_env": "PROD", "testing": True},
        {"cors_origins": "*"},
        {"cors_origins": "https://example.com/path"},
        {"testing": False, "database_url": "sqlite+pysqlite:///:memory:"},
    ],
)
def test_configuration_rejects_unsafe_defaults(overrides):
    baseline = {
        "app_env": "TEST",
        "testing": True,
        "database_url": "sqlite+pysqlite:///:memory:",
        "jwt_secret": "isolated-tests-only-never-deploy-this-key",
        "cookie_secure": True,
    }
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{**baseline, **overrides})


def test_configuration_errors_hide_input_secrets():
    secret = "sensitive-database-password"
    with pytest.raises(ValidationError) as error:
        Settings(
            _env_file=None,
            app_env="PROD",
            testing=False,
            database_url=f"postgresql+psycopg://app:{secret}@localhost/auladata",
            jwt_secret="too-short",
        )
    assert secret not in str(error.value)
    assert "too-short" not in str(error.value)


def test_seed_is_idempotent_and_passwords_are_hashed(application):
    settings = application.state.settings.model_copy(
        update={
            "admin_initial_email": "newadmin@example.com",
            "viewer_initial_email": "newviewer@example.com",
            "admin_initial_password": application.state.settings.jwt_secret,
            "viewer_initial_password": application.state.settings.jwt_secret,
            "seed_demo": True,
        }
    )
    with application.state.session_factory() as session:
        first = seed_database(session, settings)
        second = seed_database(session, settings)
        assert first == {"users": 2, "classrooms": len(DEMO_CLASSROOMS)}
        assert second == {"users": 0, "classrooms": 0}
        user = session.scalar(select(User).where(User.email == "newadmin@example.com"))
        password = settings.admin_initial_password.get_secret_value()
        assert user.password_hash != password
        assert user.password_hash.startswith("$argon2id$")
        assert verify_password(password, user.password_hash)


def test_seed_failure_rolls_back_earlier_changes(application):
    settings = application.state.settings.model_copy(
        update={
            "admin_initial_email": "newadmin@example.com",
            "admin_initial_password": application.state.settings.jwt_secret,
            "viewer_initial_email": "newviewer@example.com",
            "viewer_initial_password": None,
            "seed_demo": True,
        }
    )
    with application.state.session_factory() as session:
        before = session.scalar(select(func.count()).select_from(User))
        with pytest.raises(ValueError, match="EMAIL y PASSWORD"):
            seed_database(session, settings)
        assert session.scalar(select(func.count()).select_from(User)) == before
        assert session.scalar(select(func.count()).select_from(Classroom)) == 0


def test_alembic_upgrade_and_development_downgrade(tmp_path, monkeypatch):
    target = f"sqlite+pysqlite:///{(tmp_path / 'migrations.sqlite').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", target)
    get_settings.cache_clear()
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    try:
        command.upgrade(config, "head")
        engine = create_engine(target)
        assert {"users", "classrooms", "alembic_version"} <= set(inspect(engine).get_table_names())
        command.check(config)
        command.downgrade(config, "base")
        assert "classrooms" not in inspect(engine).get_table_names()
        engine.dispose()
    finally:
        get_settings.cache_clear()
