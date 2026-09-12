from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, utc_now


class ClassroomType(StrEnum):
    LABORATORIO = "LABORATORIO"
    TEORICA = "TEORICA"
    MIXTA = "MIXTA"


class ClassroomStatus(StrEnum):
    ACTIVA = "ACTIVA"
    MANTENIMIENTO = "MANTENIMIENTO"
    INACTIVA = "INACTIVA"


class Classroom(Base):
    __tablename__ = "classrooms"
    __table_args__ = (CheckConstraint("capacidad > 0", name="positive_capacity"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(100))
    edificio: Mapped[str] = mapped_column(String(50))
    capacidad: Mapped[int]
    tipo: Mapped[ClassroomType] = mapped_column(
        Enum(ClassroomType, name="classroom_type", native_enum=False, create_constraint=True)
    )
    estado: Mapped[ClassroomStatus] = mapped_column(
        Enum(ClassroomStatus, name="classroom_status", native_enum=False, create_constraint=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
