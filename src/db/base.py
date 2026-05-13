"""Declarative base + ULID primary key helper."""

from datetime import datetime, timezone
from ulid import ULID
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy import DateTime, String


def new_ulid() -> str:
    return str(ULID())


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


def ulid_pk(prefix: str) -> Mapped[str]:
    """Return a mapped_column for a prefixed ULID primary key (e.g., ds_01HXYZ...)."""
    return mapped_column(
        String(32),
        primary_key=True,
        default=lambda: f"{prefix}_{new_ulid()}",
    )
