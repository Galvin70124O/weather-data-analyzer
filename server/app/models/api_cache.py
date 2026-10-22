from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ApiCache(Base):
    """
    Answers from outside APIs, so we don't spend quota on the same question twice.
    Expired rows are kept: if the API is down, an old answer is still better than nothing
    (it is then marked "stale").
    """

    __tablename__ = "api_cache"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)   # e.g. "owm:current:51.5073,-0.1276"
    payload: Mapped[Any] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_api_cache_expires_at", "expires_at"),)
