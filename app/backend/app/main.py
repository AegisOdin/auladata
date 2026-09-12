import logging
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings, get_settings
from app.core.logging import configure_logging
from app.database import create_database
from app.routers import auth, classrooms

logger = logging.getLogger("auladata.api")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    engine, session_factory = create_database(settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        logger.info(
            "service_started environment=%s version=%s commit=%s",
            settings.app_env,
            settings.app_version,
            settings.git_commit,
        )
        yield
        engine.dispose()
        logger.info("service_stopped")

    application = FastAPI(
        title="AulaData API",
        description="Gestión de aulas con sesiones HttpOnly y permisos ADMIN / VIEWER.",
        version=settings.app_version,
        docs_url=None if settings.app_env == "PROD" else "/docs",
        redoc_url=None if settings.app_env == "PROD" else "/redoc",
        openapi_url=None if settings.app_env == "PROD" else "/openapi.json",
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.state.engine = engine
    application.state.session_factory = session_factory
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Requested-With"],
    )

    @application.middleware("http")
    async def request_log(request: Request, call_next):
        start = perf_counter()
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        if response.status_code >= 400:
            logger.warning(
                "request_failed method=%s path=%s status=%s duration_ms=%.1f",
                request.method,
                request.url.path,
                response.status_code,
                (perf_counter() - start) * 1000,
            )
        return response

    @application.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        logger.error("database_error method=%s type=%s", request.method, type(exc).__name__)
        return JSONResponse(status_code=503, content={"detail": "Base de datos no disponible"})

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logger.error("unexpected_error method=%s type=%s", request.method, type(exc).__name__)
        return JSONResponse(status_code=500, content={"detail": "Error interno del servicio"})

    @application.get("/health", tags=["Operación"])
    def health():
        return {
            "status": "ok",
            "service": "auladata-api",
            "environment": settings.app_env,
            "version": settings.app_version,
            "commit": settings.git_commit,
        }

    @application.get("/ready", tags=["Operación"])
    def ready():
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            logger.error("readiness_database_unavailable")
            return JSONResponse(
                status_code=503, content={"status": "error", "database": "unavailable"}
            )
        return {"status": "ok", "database": "ok"}

    application.include_router(auth.router)
    application.include_router(classrooms.router)
    return application


app = create_app()
