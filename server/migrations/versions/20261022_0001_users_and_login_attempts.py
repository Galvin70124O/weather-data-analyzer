"""users and login_attempts

Revision ID: 0001
Revises:
Create Date: 2026-10-22
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=100), nullable=False),
        sa.Column("units", sa.String(length=8), server_default="metric", nullable=False),
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("units IN ('metric', 'imperial')", name=op.f("ck_users_units_valid")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index("uq_users_username_lower", "users", [sa.text("lower(username)")], unique=True)
    op.create_index("uq_users_email_lower", "users", [sa.text("lower(email)")], unique=True)

    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("identifier", sa.String(length=254), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login_attempts")),
    )
    op.create_index("ix_login_attempts_identifier_time", "login_attempts", ["identifier", "attempted_at"])
    op.create_index("ix_login_attempts_ip_time", "login_attempts", ["ip", "attempted_at"])


def downgrade() -> None:
    op.drop_index("ix_login_attempts_ip_time", table_name="login_attempts")
    op.drop_index("ix_login_attempts_identifier_time", table_name="login_attempts")
    op.drop_table("login_attempts")
    op.drop_index("uq_users_email_lower", table_name="users")
    op.drop_index("uq_users_username_lower", table_name="users")
    op.drop_table("users")
