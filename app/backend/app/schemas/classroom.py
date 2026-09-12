from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import ClassroomStatus, ClassroomType

Key = Annotated[str, Field(min_length=1, max_length=20)]
Name = Annotated[str, Field(min_length=1, max_length=100)]
Building = Annotated[str, Field(min_length=1, max_length=50)]
Capacity = Annotated[int, Field(gt=0, le=2147483647, strict=True)]


class ClassroomInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("clave", mode="before", check_fields=False)
    @classmethod
    def normalize_key(cls, value):
        return value.strip().upper() if isinstance(value, str) else value


class ClassroomCreate(ClassroomInput):
    clave: Key
    nombre: Name
    edificio: Building
    capacidad: Capacity
    tipo: ClassroomType
    estado: ClassroomStatus


class ClassroomPatch(ClassroomInput):
    clave: Key | None = None
    nombre: Name | None = None
    edificio: Building | None = None
    capacidad: Capacity | None = None
    tipo: ClassroomType | None = None
    estado: ClassroomStatus | None = None

    @model_validator(mode="after")
    def require_non_null_changes(self) -> "ClassroomPatch":
        if not self.model_fields_set:
            raise ValueError("Incluye al menos un campo para actualizar")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Los campos del aula no pueden ser nulos")
        return self


class ClassroomResponse(ClassroomCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    @field_validator("created_at", "updated_at", "deleted_at")
    @classmethod
    def normalize_timezone(cls, value):
        # SQLite does not retain timezones; PostgreSQL uses timestamptz.
        return value.replace(tzinfo=UTC) if value and value.tzinfo is None else value


class ClassroomPage(BaseModel):
    items: list[ClassroomResponse]
    total: int
    page: int
    page_size: int
