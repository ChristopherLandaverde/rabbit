"""SQLAlchemy representation of the v2 resource model in SPEC_v2 §3."""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

JSON_VALUE = JSON().with_variant(JSONB(), "postgresql")
DATASET_STATUS = Enum("validating", "ready", "invalid", name="dataset_status")
ANALYSIS_STATUS = Enum(
    "queued", "running", "succeeded", "failed", "cancelled", name="analysis_status"
)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    key_hash: Mapped[str] = mapped_column(Text, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON_VALUE, nullable=False)
    rate_limit_per_minute: Mapped[int | None] = mapped_column(Integer)
    is_test: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def livemode(self) -> bool:
        return not self.is_test


class SignupEvent(Base):
    __tablename__ = "signup_events"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    key_id: Mapped[str] = mapped_column(ForeignKey("api_keys.id"), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(Text)
    use_case: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    key_id: Mapped[str] = mapped_column(ForeignKey("api_keys.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    touchpoint_count: Mapped[int | None] = mapped_column(Integer)
    unique_customers: Mapped[int | None] = mapped_column(Integer)
    schema_fingerprint: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(DATASET_STATUS, nullable=False)
    validation_report: Mapped[dict[str, Any] | None] = mapped_column(JSON_VALUE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Webhook(Base):
    __tablename__ = "webhooks"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    key_id: Mapped[str] = mapped_column(ForeignKey("api_keys.id"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    events: Mapped[list[str]] = mapped_column(JSON_VALUE, nullable=False)
    signing_secret_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    signing_secret_prefix: Mapped[str] = mapped_column(String(8), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Analysis(Base):
    __tablename__ = "analyses"
    __table_args__ = (
        Index("uq_analyses_key_id_idempotency_key", "key_id", "idempotency_key", unique=True),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    key_id: Mapped[str] = mapped_column(ForeignKey("api_keys.id"), nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), nullable=False, index=True)
    models: Mapped[list[str]] = mapped_column(JSON_VALUE, nullable=False)
    options: Mapped[dict[str, Any] | None] = mapped_column(JSON_VALUE)
    status: Mapped[str] = mapped_column(ANALYSIS_STATUS, nullable=False)
    progress: Mapped[dict[str, Any] | None] = mapped_column(JSON_VALUE)
    results: Mapped[dict[str, Any] | None] = mapped_column(JSON_VALUE)
    comparison: Mapped[dict[str, Any] | None] = mapped_column(JSON_VALUE)
    idempotency_key: Mapped[str | None] = mapped_column(Text)
    last_progress_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    webhook_id: Mapped[str | None] = mapped_column(ForeignKey("webhooks.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[dict[str, Any] | None] = mapped_column(JSON_VALUE)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    webhook_id: Mapped[str] = mapped_column(ForeignKey("webhooks.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_VALUE, nullable=False)
    response_code: Mapped[int | None] = mapped_column(Integer)
    response_body: Mapped[str | None] = mapped_column(Text)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    key_id: Mapped[str | None] = mapped_column(ForeignKey("api_keys.id"), index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[str | None] = mapped_column(String(64))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
