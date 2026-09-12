import logging
import sys

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.config import Settings, get_settings
from app.core.logging import configure_logging
from app.database import create_database
from app.models import Classroom, ClassroomStatus, ClassroomType, Role, User

logger = logging.getLogger("auladata.seed")

DEMO_CLASSROOMS = [
    ("ISC-A01", "Laboratorio de Redes", "Edificio K", 30, "LABORATORIO", "ACTIVA"),
    ("ISC-A02", "Aula de Software", "Edificio J", 35, "TEORICA", "ACTIVA"),
    ("ISC-A03", "Laboratorio de Sistemas", "Edificio L", 25, "MIXTA", "MANTENIMIENTO"),
    ("ISC-A04", "Laboratorio de Arquitectura", "Edificio K", 28, "LABORATORIO", "ACTIVA"),
    ("ISC-A05", "Aula de Matemáticas", "Edificio J", 40, "TEORICA", "ACTIVA"),
    ("ISC-A06", "Sala de Proyectos", "Edificio L", 20, "MIXTA", "INACTIVA"),
]


def seed_database(session: Session, settings: Settings) -> dict[str, int]:
    users = [
        (
            Role.ADMIN,
            settings.admin_initial_name,
            settings.admin_initial_email,
            settings.admin_initial_password,
        ),
        (
            Role.VIEWER,
            settings.viewer_initial_name,
            settings.viewer_initial_email,
            settings.viewer_initial_password,
        ),
    ]
    configured_emails = [str(email).lower() for _, _, email, _ in users if email]
    if len(configured_emails) != len(set(configured_emails)):
        raise ValueError("ADMIN y VIEWER deben tener correos diferentes")
    created = {"users": 0, "classrooms": 0}
    try:
        for role, name, email, password in users:
            if not email and not password:
                continue
            if not email or not password:
                raise ValueError(f"Configura EMAIL y PASSWORD para {role}")
            normalized = str(email).lower()
            if session.scalar(select(User.id).where(User.email == normalized)):
                continue
            if not 12 <= len(password.get_secret_value()) <= 128:
                raise ValueError(
                    f"La contraseña inicial {role} debe tener entre 12 y 128 caracteres"
                )
            if not name.strip() or len(name.strip()) > 100:
                raise ValueError(f"El nombre inicial {role} debe tener entre 1 y 100 caracteres")
            session.add(
                User(
                    name=name.strip(),
                    email=normalized,
                    password_hash=hash_password(password.get_secret_value()),
                    role=role,
                    is_active=True,
                )
            )
            created["users"] += 1
        if settings.seed_demo:
            for clave, nombre, edificio, capacidad, tipo, estado in DEMO_CLASSROOMS:
                if session.scalar(select(Classroom.id).where(Classroom.clave == clave)):
                    continue
                session.add(
                    Classroom(
                        clave=clave,
                        nombre=nombre,
                        edificio=edificio,
                        capacidad=capacidad,
                        tipo=ClassroomType(tipo),
                        estado=ClassroomStatus(estado),
                    )
                )
                created["classrooms"] += 1
        session.commit()
    except Exception:
        session.rollback()
        raise
    return created


def main() -> int:
    try:
        settings = get_settings()
        configure_logging(settings.log_level)
        engine, factory = create_database(settings)
        try:
            with factory() as session:
                created = seed_database(session, settings)
        finally:
            engine.dispose()
    except (ValidationError, ValueError, SQLAlchemyError) as exc:
        # Only safe explicit ValueError messages; DB/config exceptions may embed secrets.
        message = str(exc) if type(exc) is ValueError else type(exc).__name__
        logger.error("seed_failed reason=%s", message)
        return 1
    logger.info("seed_complete users_created=%s classrooms_created=%s", *created.values())
    return 0


if __name__ == "__main__":
    sys.exit(main())
