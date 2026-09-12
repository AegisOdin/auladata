from collections.abc import Generator
from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def create_database(settings: Settings):
    url = settings.database_url.get_secret_value()
    options = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        options.update(connect_args={"check_same_thread": False}, poolclass=StaticPool)
    else:
        options.update(pool_size=3, max_overflow=2, connect_args={"connect_timeout": 5})
    engine = create_engine(url, **options)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def get_session(request: Request) -> Generator[Session]:
    with request.app.state.session_factory() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
