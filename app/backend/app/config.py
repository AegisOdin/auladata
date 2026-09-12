from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import EmailStr, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: Literal["DEV", "QA", "PROD", "TEST"] = "DEV"
    app_version: str = "development"
    git_commit: str = "unknown"
    database_url: SecretStr
    jwt_secret: SecretStr
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_expires_minutes: int = Field(default=60, ge=1, le=1440)
    cookie_secure: bool = True
    cors_origins: str = "http://localhost:3000"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    testing: bool = False
    admin_initial_name: str = "Administración AulaData"
    admin_initial_email: EmailStr | None = None
    admin_initial_password: SecretStr | None = None
    viewer_initial_name: str = "Consulta AulaData"
    viewer_initial_email: EmailStr | None = None
    viewer_initial_password: SecretStr | None = None
    seed_demo: bool = False

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()
        ]

    @model_validator(mode="after")
    def validate_configuration(self) -> "Settings":
        if len(self.jwt_secret.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET debe contener al menos 32 caracteres aleatorios")
        try:
            database = make_url(self.database_url.get_secret_value())
        except Exception as exc:
            raise ValueError("DATABASE_URL no tiene un formato válido") from exc
        if database.drivername != "postgresql+psycopg" and not (
            self.testing and self.app_env == "TEST" and database.drivername == "sqlite+pysqlite"
        ):
            raise ValueError("DATABASE_URL debe usar postgresql+psycopg")
        if self.testing and self.app_env != "TEST":
            raise ValueError("TESTING solo está permitido con APP_ENV=TEST")
        if self.app_env in {"QA", "PROD"} and not self.cookie_secure:
            raise ValueError("QA y PROD requieren COOKIE_SECURE=true y HTTPS")
        for origin in self.allowed_origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
                or "*" in origin
            ):
                raise ValueError(
                    "CORS_ORIGINS debe contener orígenes explícitos separados por comas"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


if __name__ == "__main__":
    import sys

    from pydantic import ValidationError

    try:
        configuration = get_settings()
    except ValidationError:
        # Pydantic exceptions may include input values; never print raw configuration errors.
        print("Configuración inválida: revisa DATABASE_URL, JWT_SECRET, APP_ENV y cookies.")
        sys.exit(1)
    print(f"Configuración válida: environment={configuration.app_env}")
