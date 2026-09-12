"""Create users and classrooms with logical deletion.

Revision ID: 20260912_0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "20260912_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("ADMIN", "VIEWER", name="user_role", native_enum=False, create_constraint=True),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "classrooms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("clave", sa.String(20), nullable=False),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("edificio", sa.String(50), nullable=False),
        sa.Column("capacidad", sa.Integer(), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum(
                "LABORATORIO",
                "TEORICA",
                "MIXTA",
                name="classroom_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "estado",
            sa.Enum(
                "ACTIVA",
                "MANTENIMIENTO",
                "INACTIVA",
                name="classroom_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("capacidad > 0", name=op.f("ck_classrooms_positive_capacity")),
        sa.PrimaryKeyConstraint("id", name="pk_classrooms"),
        sa.UniqueConstraint("clave", name="uq_classrooms_clave"),
    )
    op.create_index("ix_classrooms_deleted_at", "classrooms", ["deleted_at"])


def downgrade() -> None:
    # Destructive development-only reset; application rollback does not call downgrade.
    op.drop_index("ix_classrooms_deleted_at", table_name="classrooms")
    op.drop_table("classrooms")
    op.drop_table("users")
