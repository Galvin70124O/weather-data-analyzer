from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LoginAttempt(Base):
    """One login try. Used for rate limiting; kept in the database so restarts don't reset the limit."""

    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    identifier: Mapped[str] = mapped_column(String(254))   # lowercased username or email that was tried
    ip: Mapped[str] = mapped_column(String(45))             # IPv6 addresses are up to 45 characters
    succeeded: Mapped[bool] = mapped_column(Boolean)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_login_attempts_identifier_time", "identifier", "attempted_at"),
        Index("ix_login_attempts_ip_time", "ip", "attempted_at"),
    )
