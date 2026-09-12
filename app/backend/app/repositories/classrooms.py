from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Classroom, ClassroomStatus, ClassroomType


def get_active(session: Session, classroom_id: int) -> Classroom | None:
    return session.scalar(
        select(Classroom).where(Classroom.id == classroom_id, Classroom.deleted_at.is_(None))
    )


def key_exists(session: Session, clave: str, excluding_id: int | None = None) -> bool:
    query = select(Classroom.id).where(Classroom.clave == clave)
    if excluding_id is not None:
        query = query.where(Classroom.id != excluding_id)
    return session.scalar(query) is not None


def list_classrooms(
    session: Session,
    *,
    search: str | None,
    estado: ClassroomStatus | None,
    tipo: ClassroomType | None,
    page: int,
    page_size: int,
) -> tuple[list[Classroom], int]:
    filters = [Classroom.deleted_at.is_(None)]
    if search and search.strip():
        # Escape LIKE wildcards so searches match the literal text entered by the user.
        term = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{term}%"
        filters.append(
            or_(
                Classroom.clave.ilike(pattern, escape="\\"),
                Classroom.nombre.ilike(pattern, escape="\\"),
                Classroom.edificio.ilike(pattern, escape="\\"),
            )
        )
    if estado is not None:
        filters.append(Classroom.estado == estado)
    if tipo is not None:
        filters.append(Classroom.tipo == tipo)
    total = session.scalar(select(func.count()).select_from(Classroom).where(*filters)) or 0
    query = (
        select(Classroom)
        .where(*filters)
        .order_by(Classroom.clave, Classroom.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(session.scalars(query)), total
