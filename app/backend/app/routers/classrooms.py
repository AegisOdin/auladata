from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from app.dependencies.auth import AdminUser, CurrentUser, DatabaseSession, verify_csrf
from app.models import ClassroomStatus, ClassroomType
from app.repositories.classrooms import list_classrooms
from app.schemas.classroom import (
    ClassroomCreate,
    ClassroomPage,
    ClassroomPatch,
    ClassroomResponse,
)
from app.services.classrooms import (
    create_classroom,
    find_classroom,
    soft_delete_classroom,
    update_classroom,
)

router = APIRouter(
    prefix="/api/v1/classrooms",
    tags=["Aulas"],
    responses={401: {"description": "Sin sesión válida"}, 403: {"description": "Permiso denegado"}},
)
ClassroomId = Annotated[int, Path(gt=0)]
MutationChecks = [Depends(verify_csrf)]


@router.get("", response_model=ClassroomPage)
def index(
    session: DatabaseSession,
    user: CurrentUser,
    search: Annotated[str | None, Query(max_length=100)] = None,
    estado: ClassroomStatus | None = None,
    tipo: ClassroomType | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    items, total = list_classrooms(
        session, search=search, estado=estado, tipo=tipo, page=page, page_size=page_size
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get(
    "/{classroom_id}",
    response_model=ClassroomResponse,
    responses={404: {"description": "Aula no encontrada"}},
)
def show(classroom_id: ClassroomId, session: DatabaseSession, user: CurrentUser):
    return find_classroom(session, classroom_id)


@router.post(
    "",
    status_code=201,
    response_model=ClassroomResponse,
    dependencies=MutationChecks,
    responses={409: {"description": "Clave duplicada"}},
)
def create(payload: ClassroomCreate, session: DatabaseSession, user: AdminUser):
    return create_classroom(session, payload)


@router.put(
    "/{classroom_id}",
    response_model=ClassroomResponse,
    dependencies=MutationChecks,
    responses={404: {"description": "Aula no encontrada"}, 409: {"description": "Clave duplicada"}},
)
def replace(
    classroom_id: ClassroomId,
    payload: ClassroomCreate,
    session: DatabaseSession,
    user: AdminUser,
):
    return update_classroom(session, classroom_id, payload)


@router.patch(
    "/{classroom_id}",
    response_model=ClassroomResponse,
    dependencies=MutationChecks,
    responses={404: {"description": "Aula no encontrada"}, 409: {"description": "Clave duplicada"}},
)
def update(
    classroom_id: ClassroomId,
    payload: ClassroomPatch,
    session: DatabaseSession,
    user: AdminUser,
):
    return update_classroom(session, classroom_id, payload)


@router.delete("/{classroom_id}", status_code=204, dependencies=MutationChecks)
def delete(classroom_id: ClassroomId, session: DatabaseSession, user: AdminUser):
    soft_delete_classroom(session, classroom_id)
    return Response(status_code=204)
