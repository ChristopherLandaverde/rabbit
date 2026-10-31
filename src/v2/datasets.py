"""Dataset upload, validation, and lifecycle endpoints."""

import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from ..core.validation.validators import validate_data_types, validate_required_columns
from ..db.models import Dataset
from ..utils.touchpoint_frames import read_touchpoint_frame
from ..db.session import get_session
from .auth.dependencies import require_api_key, require_scope
from .auth.errors import ApiProblem
from .storage import LocalDiskStorage, S3Storage
from .storage.base import dataset_storage_key

router = APIRouter(tags=["Datasets"])
MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024
SUPPORTED_EXTENSIONS = {"csv", "json", "parquet"}


class ValidationIssue(BaseModel):
    row: int | None = None
    column: str | None = None
    code: str
    message: str


class ValidationReport(BaseModel):
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)


def get_storage():
    backend = os.getenv("RABBIT_STORAGE_BACKEND", "local").lower()
    if backend == "s3":
        bucket = os.getenv("RABBIT_S3_BUCKET")
        if not bucket:
            raise RuntimeError(
                "RABBIT_S3_BUCKET is required when RABBIT_STORAGE_BACKEND=s3"
            )
        return S3Storage(
            bucket, os.getenv("AWS_REGION"), os.getenv("RABBIT_S3_ENDPOINT_URL")
        )
    return LocalDiskStorage(os.getenv("RABBIT_STORAGE_DIR", "uploads"))


def _read_frame(content: bytes, extension: str) -> pd.DataFrame:
    # Identifier columns stay text so numeric-looking ids keep every row (#66).
    return read_touchpoint_frame(content, extension)


def _validation_report(
    frame: pd.DataFrame | None, parse_error: Exception | None = None
):
    if parse_error:
        return ValidationReport(
            errors=[
                ValidationIssue(
                    row=None,
                    column=None,
                    code="invalid_file_format",
                    message=f"Could not parse uploaded dataset: {str(parse_error)[:300]}",
                )
            ]
        )
    issues = []
    for error in validate_required_columns(frame):
        issues.append(
            ValidationIssue(
                column=error.field, code=error.error_code, message=error.message
            )
        )
    for error in validate_data_types(frame):
        issues.append(
            ValidationIssue(
                column=error.field, code=error.error_code, message=error.message
            )
        )
    return ValidationReport(errors=issues)


def _dropped_row_warnings(frame: pd.DataFrame) -> list[ValidationIssue]:
    """Warn when rows will not become touchpoints in an analysis (#66).

    Builds touchpoints the way analyses do and reports how many rows fall out
    and the first reason, so data loss is visible at upload time.
    """
    from ..core.identity.journey_builder import JourneyBuilder

    normalized = frame.copy()
    normalized.columns = normalized.columns.str.lower()
    if "timestamp" in normalized.columns:
        normalized["timestamp"] = pd.to_datetime(normalized["timestamp"], errors="coerce")
    # Collect reasons rather than redirecting stdout, which is process-wide
    # and races with other threads.
    errors: list[str] = []
    built = JourneyBuilder()._create_touchpoints(normalized, errors=errors)
    dropped = len(normalized) - len(built)
    if dropped <= 0:
        return []
    reason = errors[0].splitlines()[0].strip() if errors else ""
    return [
        ValidationIssue(
            code="rows_dropped",
            message=(
                f"{dropped} of {len(normalized)} rows cannot become touchpoints and will be "
                f"left out of analyses. First reason: {reason[:300]}"
            ),
        )
    ]


def _dataset_response(dataset: Dataset):
    validation = ValidationReport.model_validate(
        dataset.validation_report or {"errors": [], "warnings": []}
    )
    return {
        "id": dataset.id,
        "name": dataset.name,
        "status": dataset.status,
        "filename": dataset.filename,
        "size_bytes": dataset.size_bytes,
        "touchpoint_count": dataset.touchpoint_count,
        "unique_customers": dataset.unique_customers,
        "schema_fingerprint": dataset.schema_fingerprint,
        "validation": validation.model_dump(),
        "created_at": dataset.created_at.isoformat(),
        "ready_at": dataset.ready_at.isoformat() if dataset.ready_at else None,
    }


async def validate_dataset(dataset_id: str, session_factory, storage):
    """Claim and validate one queued dataset; SKIP LOCKED prevents duplicate workers."""
    async with session_factory() as session:
        statement = (
            select(Dataset)
            .where(
                Dataset.id == dataset_id,
                Dataset.status == "validating",
                Dataset.deleted_at.is_(None),
            )
            .with_for_update(skip_locked=True)
        )
        dataset = (await session.execute(statement)).scalar_one_or_none()
        if dataset is None:
            return
        try:
            raw = storage.read(dataset.storage_uri)
            extension = Path(dataset.filename).suffix.lower().lstrip(".")
            frame = _read_frame(raw, extension)
            report = _validation_report(frame)
            if not report.errors:
                report.warnings.extend(_dropped_row_warnings(frame))
            dataset.touchpoint_count = len(frame)
            dataset.unique_customers = (
                int(frame["customer_id"].nunique()) if "customer_id" in frame else None
            )
            schema = json.dumps(
                [
                    {"name": str(column), "dtype": str(dtype)}
                    for column, dtype in zip(frame.columns, frame.dtypes)
                ],
                separators=(",", ":"),
            )
            dataset.schema_fingerprint = (
                "sha256:" + hashlib.sha256(schema.encode()).hexdigest()
            )
        except Exception as exc:
            report = _validation_report(None, exc)
        dataset.validation_report = report.model_dump()
        dataset.status = "invalid" if report.errors else "ready"
        dataset.ready_at = (
            datetime.now(timezone.utc) if dataset.status == "ready" else None
        )
        await session.commit()


@router.post(
    "/datasets",
    status_code=202,
    dependencies=[Depends(require_scope("datasets:write"))],
)
async def create_dataset(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    key=Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    filename = Path(file.filename or "dataset").name
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension not in SUPPORTED_EXTENSIONS:
        raise ApiProblem(
            422,
            "unsupported_file_type",
            "Unsupported file type",
            "Upload a CSV, JSON, or Parquet file.",
            "Choose a .csv, .json, or .parquet file.",
            "https://docs.rabbit.example/datasets",
        )
    chunks, size = [], 0
    while chunk := await file.read(1024 * 1024):
        size += len(chunk)
        if size > MAX_FILE_SIZE_BYTES:
            raise ApiProblem(
                413,
                "file_too_large",
                "File too large",
                "Dataset uploads are limited to 500 MB.",
                "Reduce the file size or use the signed upload flow when available.",
                "https://docs.rabbit.example/datasets#limits",
            )
        chunks.append(chunk)
    if size == 0:
        raise ApiProblem(
            422,
            "empty_file",
            "Empty file",
            "The uploaded file is empty.",
            "Upload a non-empty dataset.",
            "https://docs.rabbit.example/datasets",
        )
    dataset_id = str(ULID())
    storage = getattr(request.app.state, "dataset_storage", None) or get_storage()
    storage_key = dataset_storage_key(key.id, dataset_id, extension)
    storage_uri = storage.put(storage_key, b"".join(chunks))
    dataset = Dataset(
        id=dataset_id,
        key_id=key.id,
        name=name or Path(filename).stem[:255],
        filename=filename,
        storage_uri=storage_uri,
        size_bytes=size,
        status="validating",
        created_at=datetime.now(timezone.utc),
    )
    session.add(dataset)
    await session.commit()
    session_factory = getattr(request.app.state, "api_session_factory", None)
    if session_factory is None:
        from ..db.session import async_session_factory

        session_factory = async_session_factory
    background_tasks.add_task(validate_dataset, dataset_id, session_factory, storage)
    return {
        "id": dataset.id,
        "name": dataset.name,
        "status": dataset.status,
        "filename": filename,
        "size_bytes": size,
        "touchpoint_count": None,
        "created_at": dataset.created_at.isoformat(),
    }


@router.get(
    "/datasets/{dataset_id}", dependencies=[Depends(require_scope("datasets:read"))]
)
async def get_dataset(
    dataset_id: str,
    key=Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    dataset = (
        await session.execute(
            select(Dataset).where(
                Dataset.id == dataset_id,
                Dataset.key_id == key.id,
                Dataset.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if dataset is None:
        raise ApiProblem(
            404,
            "not_found",
            "Dataset not found",
            "No dataset has that id.",
            "Check the dataset id.",
            "https://docs.rabbit.example/datasets",
        )
    return _dataset_response(dataset)


@router.get("/datasets", dependencies=[Depends(require_scope("datasets:read"))])
async def list_datasets(
    limit: int = 20,
    cursor: str | None = None,
    key=Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    if limit < 1 or limit > 100:
        raise ApiProblem(
            422,
            "invalid_limit",
            "Invalid page size",
            "limit must be between 1 and 100.",
            "Set limit to a value from 1 to 100.",
            "https://docs.rabbit.example/pagination",
        )
    statement = (
        select(Dataset)
        .where(Dataset.key_id == key.id, Dataset.deleted_at.is_(None))
        .order_by(Dataset.created_at.desc(), Dataset.id.desc())
    )
    if cursor:
        try:
            after_id = base64.urlsafe_b64decode(
                cursor + "=" * (-len(cursor) % 4)
            ).decode()
        except Exception as exc:
            raise ApiProblem(
                422,
                "invalid_cursor",
                "Invalid cursor",
                "The cursor is malformed.",
                "Use the next_cursor from the previous page.",
                "https://docs.rabbit.example/pagination",
            ) from exc
        after = await session.get(Dataset, after_id)
        if after is None or after.key_id != key.id:
            raise ApiProblem(
                422,
                "invalid_cursor",
                "Invalid cursor",
                "The cursor does not identify a dataset in this scope.",
                "Use the next_cursor from the previous page.",
                "https://docs.rabbit.example/pagination",
            )
        statement = statement.where(
            (Dataset.created_at < after.created_at)
            | ((Dataset.created_at == after.created_at) & (Dataset.id < after.id))
        )
    rows = (await session.execute(statement.limit(limit + 1))).scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = (
        base64.urlsafe_b64encode(page[-1].id.encode()).decode().rstrip("=")
        if has_more and page
        else None
    )
    return {
        "data": [_dataset_response(dataset) for dataset in page],
        "next_cursor": next_cursor,
        "has_more": has_more,
    }


@router.delete(
    "/datasets/{dataset_id}",
    status_code=204,
    dependencies=[Depends(require_scope("datasets:delete"))],
)
async def delete_dataset(
    dataset_id: str,
    key=Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    dataset = (
        await session.execute(
            select(Dataset).where(
                Dataset.id == dataset_id,
                Dataset.key_id == key.id,
                Dataset.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if dataset is None:
        raise ApiProblem(
            404,
            "not_found",
            "Dataset not found",
            "No dataset has that id.",
            "Check the dataset id.",
            "https://docs.rabbit.example/datasets",
        )
    dataset.deleted_at = datetime.now(timezone.utc)
    await session.commit()
