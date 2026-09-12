from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import utc_now
from app.models import Classroom, ClassroomStatus
from app.repositories import classrooms as repository
from app.schemas.classroom import ClassroomCreate, ClassroomPatch


def find_classroom(session: Session, classroom_id: int) -> Classroom:
    classroom = repository.get_active(session, classroom_id)
    if classroom is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aula no encontrada")
    return classroom


def commit_classroom(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        sqlstate = getattr(exc.orig, "sqlstate", None)
        if sqlstate == "23505" or "UNIQUE constraint failed: classrooms.clave" in str(exc.orig):
            raise HTTPException(status.HTTP_409_CONFLICT, "La clave ya está registrada") from None
        raise


def create_classroom(session: Session, payload: ClassroomCreate) -> Classroom:
    if repository.key_exists(session, payload.clave):
        raise HTTPException(status.HTTP_409_CONFLICT, "La clave ya está registrada")
    classroom = Classroom(**payload.model_dump())
    session.add(classroom)
    commit_classroom(session)
    session.refresh(classroom)
    return classroom


def update_classroom(
    session: Session, classroom_id: int, payload: ClassroomCreate | ClassroomPatch
) -> Classroom:
    classroom = find_classroom(session, classroom_id)
    changes = payload.model_dump(exclude_unset=True)
    if "clave" in changes and repository.key_exists(session, changes["clave"], classroom_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "La clave ya está registrada")
    for field, value in changes.items():
        setattr(classroom, field, value)
    commit_classroom(session)
    session.refresh(classroom)
    return classroom


def soft_delete_classroom(session: Session, classroom_id: int) -> None:
    classroom = find_classroom(session, classroom_id)
    classroom.deleted_at = utc_now()
    classroom.estado = ClassroomStatus.INACTIVA
    commit_classroom(session)
