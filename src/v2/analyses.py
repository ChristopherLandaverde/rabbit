"""Single-model async attribution analyses (#16).

An analysis applies one named, rule-based attribution model to a ready dataset.
The credits it returns describe how conversions are distributed across channels
under that model's rule. They are associations, not measured causal impact.
"""

import asyncio
import base64
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from ..core.attribution.factory import AttributionModelFactory
from ..core.attribution_service import AttributionService
from ..core.identity.resolver import IdentityResolver, select_linking_method
from ..core.validation.validators import validate_data_quality
from ..db.models import Analysis, Dataset
from ..db.session import get_session
from ..models.enums import AttributionModelType
from .auth.dependencies import require_api_key, require_scope
from .auth.errors import ApiProblem
from .datasets import _read_frame, get_storage

router = APIRouter(tags=["Analyses"])
logger = logging.getLogger(__name__)

MAX_ANALYSIS_TOUCHPOINTS = 250_000
MAX_MODELS_PER_ANALYSIS = 1
ANALYSIS_STATUSES = ("queued", "running", "succeeded", "failed", "cancelled")
DOCS = "https://docs.rabbit.example/analyses"
SUPPORTED_OPTIONS = {"time_decay_half_life_days", "position_based_weights"}

INTERPRETATION_TYPE = "association"
ANALYSIS_DESCRIPTION = (
    "Queue one rule-based attribution model (first_touch, last_touch, linear, "
    "time_decay or position_based) against a ready dataset, then poll "
    "GET /v2/analyses/{id}. Each channel's credit is its share of conversions "
    "under the named model's rule, an association: it is not causal impact or "
    "incrementality and does not say what would happen if spend changed."
)


class AnalysisCreate(BaseModel):
    dataset_id: str
    models: list[str]
    options: dict[str, Any] | None = None


def _interpretation(models: list[str]) -> dict[str, str]:
    names = ", ".join(models)
    return {
        "type": INTERPRETATION_TYPE,
        "statement": (
            f"Credits show how conversions are shared across channels under the "
            f"named model ({names}) and its parameters. They describe an "
            f"association in this dataset, not causal effect or incrementality."
        ),
    }


def _invalid(code: str, detail: str, fix_hint: str, status: int = 422) -> ApiProblem:
    return ApiProblem(status, code, "Invalid analysis request", detail, fix_hint, DOCS)


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def resolve_parameters(model: str, options: dict[str, Any] | None) -> dict[str, float]:
    """Validate request options and return the model's effective parameters."""
    options = options or {}
    unknown = sorted(set(options) - SUPPORTED_OPTIONS)
    if unknown:
        raise _invalid(
            "validation_failed",
            f"Unsupported option(s): {', '.join(unknown)}.",
            "Use time_decay_half_life_days or position_based_weights.",
        )
    half_life = options.get("time_decay_half_life_days", 7.0)
    if not _number(half_life) or half_life <= 0:
        raise _invalid(
            "validation_failed",
            "options.time_decay_half_life_days must be a positive number.",
            "Set time_decay_half_life_days to a number of days above 0, e.g. 7.",
        )
    weights = options.get("position_based_weights", {})
    if not isinstance(weights, dict) or set(weights) - {"first", "last", "middle"}:
        raise _invalid(
            "validation_failed",
            "options.position_based_weights accepts first, last and middle.",
            'Send {"first": 0.4, "last": 0.4}.',
        )
    first, last = weights.get("first", 0.4), weights.get("last", 0.4)
    if not (_number(first) and _number(last) and 0 <= first <= 1 and 0 <= last <= 1
            and first + last <= 1 + 1e-9):
        raise _invalid(
            "validation_failed",
            "position_based_weights.first and .last must be between 0 and 1 and sum to at most 1.",
            "Choose first and last weights whose sum is 1 or less.",
        )
    middle = 1.0 - first - last
    if "middle" in weights and (not _number(weights["middle"])
                                or abs(weights["middle"] - middle) > 1e-9):
        raise _invalid(
            "validation_failed",
            "position_based_weights.middle must equal 1 - first - last.",
            "Omit middle; it is derived from first and last.",
        )
    if model == AttributionModelType.TIME_DECAY.value:
        return {"half_life_days": float(half_life)}
    if model == AttributionModelType.POSITION_BASED.value:
        return {
            "first_touch_weight": float(first),
            "last_touch_weight": float(last),
            "middle_touch_weight": middle,
        }
    return {}


def compute_model_result(frame: pd.DataFrame, model: str, parameters: dict[str, float]):
    """Run one v1 attribution model on a dataset frame.

    Mirrors AttributionService.analyze_attribution steps 1-5 and reuses its
    credit calculation, so credits equal the v1 /attribution/analyze output.
    """
    frame = frame.copy()
    frame.columns = frame.columns.str.lower()
    if "timestamp" in frame.columns:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    service = AttributionService()
    errors = service._validate_data(frame)
    if errors:
        raise ValueError(f"Data validation failed: {errors}")
    linking_method = select_linking_method(frame)
    identity_map = IdentityResolver(linking_method).resolve_identities(frame)
    journeys = service.journey_builder.build_journeys(frame, identity_map)
    model_kwargs = {k: v for k, v in parameters.items() if k != "middle_touch_weight"}
    attribution_model = AttributionModelFactory.create_model(
        AttributionModelType(model), **model_kwargs
    )
    channels = service._calculate_attribution(
        journeys, attribution_model, validate_data_quality(frame)
    )
    converting = [journey for journey in journeys if journey.has_conversion]
    summary = {
        "touchpoints": len(frame),
        "journeys": len(journeys),
        "converting_journeys": len(converting),
        "total_conversions": sum(j.total_conversions for j in converting),
        "total_revenue": sum(j.total_revenue for j in converting),
        "linking_method": linking_method.value,
    }
    result = {
        "model": model,
        "parameters": parameters,
        "channels": {
            channel: {
                "credit": value.credit,
                "conversions": value.conversions,
                "revenue": value.revenue,
            }
            for channel, value in sorted(
                channels.items(), key=lambda item: item[1].credit, reverse=True
            )
        },
    }
    return summary, result


async def claim_next_analysis(session_factory) -> str | None:
    """Move the oldest queued analysis to running; SKIP LOCKED lets workers race safely."""
    async with session_factory() as session:
        statement = (
            select(Analysis)
            .where(Analysis.status == "queued")
            .order_by(Analysis.created_at, Analysis.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        analysis = (await session.execute(statement)).scalar_one_or_none()
        if analysis is None:
            return None
        now = datetime.now(timezone.utc)
        analysis.status = "running"
        analysis.started_at = now
        analysis.last_progress_at = now
        analysis.progress = {"models_completed": 0, "models_total": len(analysis.models)}
        await session.commit()
        return analysis.id


async def execute_analysis(analysis_id: str, session_factory, storage) -> None:
    """Run every model of a claimed analysis and store the results."""
    async with session_factory() as session:
        analysis = await session.get(Analysis, analysis_id)
        if analysis is None or analysis.status != "running":
            return
        try:
            dataset = await session.get(Dataset, analysis.dataset_id)
            raw = storage.read(dataset.storage_uri)
            extension = Path(dataset.filename).suffix.lower().lstrip(".")
            frame = _read_frame(raw, extension)
            parameters = (analysis.options or {}).get("parameters", {})
            summary, models = None, {}
            for index, model in enumerate(analysis.models, start=1):
                summary, models[model] = await asyncio.to_thread(
                    compute_model_result, frame, model, parameters.get(model, {})
                )
                analysis.progress = {
                    "models_completed": index,
                    "models_total": len(analysis.models),
                }
                analysis.last_progress_at = datetime.now(timezone.utc)
                await session.commit()
            analysis.results = {"summary": summary, "models": models}
            analysis.status = "succeeded"
        except Exception as exc:
            await session.rollback()
            analysis = await session.get(Analysis, analysis_id)
            analysis.status = "failed"
            analysis.error = {
                "code": "analysis_failed",
                "message": f"The model could not be run on this dataset: {str(exc)[:300]}",
            }
        analysis.completed_at = datetime.now(timezone.utc)
        analysis.last_progress_at = analysis.completed_at
        await session.commit()


async def process_queued_analyses(session_factory, storage) -> int:
    """Claim and run queued analyses until none remain; returns how many ran."""
    processed = 0
    while (analysis_id := await claim_next_analysis(session_factory)) is not None:
        await execute_analysis(analysis_id, session_factory, storage)
        processed += 1
    return processed


async def run_worker(session_factory, storage, poll_seconds: float = 1.0,
                     stop: asyncio.Event | None = None) -> None:
    """Long-running worker loop: drain the queue, then poll for new work."""
    stop = stop or asyncio.Event()
    while not stop.is_set():
        try:
            processed = await process_queued_analyses(session_factory, storage)
        except Exception:
            logger.exception("Analysis worker iteration failed; retrying")
            processed = 0
        if processed == 0:
            try:
                await asyncio.wait_for(stop.wait(), timeout=poll_seconds)
            except TimeoutError:
                pass


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _analysis_response(analysis: Analysis, livemode: bool, include_results: bool = True):
    body = {
        "id": analysis.id,
        "object": "analysis",
        "livemode": livemode,
        "status": analysis.status,
        "dataset_id": analysis.dataset_id,
        "models": analysis.models,
        "options": (analysis.options or {}).get("request", {}),
        "progress": analysis.progress,
        "interpretation": _interpretation(analysis.models),
        "created_at": _iso(analysis.created_at),
        "started_at": _iso(analysis.started_at),
        "completed_at": _iso(analysis.completed_at),
        "error": analysis.error,
    }
    if include_results:
        results = analysis.results or {}
        body["summary"] = results.get("summary")
        body["results"] = results.get("models")
    return body


def _not_found(detail="No analysis has that id.") -> ApiProblem:
    return ApiProblem(404, "not_found", "Analysis not found", detail, "Check the analysis id.", DOCS)


@router.post(
    "/analyses",
    status_code=202,
    summary="Run one attribution model on a dataset",
    description=ANALYSIS_DESCRIPTION,
    dependencies=[Depends(require_scope("analyses:write"))],
)
async def create_analysis(
    payload: AnalysisCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    key=Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    if not payload.models:
        raise _invalid("validation_failed", "models must name one model.", 'Send "models": ["linear"].')
    valid = [model.value for model in AttributionModelType]
    unknown = [model for model in payload.models if model not in valid]
    if unknown:
        raise _invalid(
            "unknown_model",
            f"Unknown model(s): {', '.join(unknown)}. Registered models: {', '.join(valid)}.",
            "Choose one of the registered models.",
        )
    if len(payload.models) > MAX_MODELS_PER_ANALYSIS:
        raise _invalid(
            "too_many_models",
            "An analysis currently runs exactly one model.",
            "Submit one analysis per model.",
        )
    parameters = {model: resolve_parameters(model, payload.options) for model in payload.models}

    dataset = (
        await session.execute(
            select(Dataset).where(
                Dataset.id == payload.dataset_id,
                Dataset.key_id == key.id,
                Dataset.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if dataset is None:
        raise ApiProblem(
            404, "not_found", "Dataset not found", "No dataset has that id.",
            "Check the dataset id; datasets are visible only to the key that uploaded them.",
            "https://docs.rabbit.example/datasets",
        )
    if dataset.status != "ready":
        raise ApiProblem(
            409, "dataset_not_ready", "Dataset not ready",
            f"Dataset {dataset.id} is {dataset.status}.",
            f"Poll GET /v2/datasets/{dataset.id} until status=ready; invalid datasets must be fixed and re-uploaded.",
            "https://docs.rabbit.example/errors#dataset_not_ready",
        )
    if (dataset.touchpoint_count or 0) > MAX_ANALYSIS_TOUCHPOINTS:
        raise ApiProblem(
            413, "dataset_too_large", "Dataset too large",
            f"Dataset {dataset.id} has {dataset.touchpoint_count} touchpoints; "
            f"analyses are limited to {MAX_ANALYSIS_TOUCHPOINTS:,}.",
            "Split the dataset into smaller date ranges and analyze each one.",
            "https://docs.rabbit.example/errors#dataset_too_large",
        )

    analysis = Analysis(
        id=str(ULID()),
        key_id=key.id,
        dataset_id=dataset.id,
        models=payload.models,
        options={"request": payload.options or {}, "parameters": parameters},
        status="queued",
        created_at=datetime.now(timezone.utc),
    )
    session.add(analysis)
    await session.commit()

    if getattr(request.app.state, "analysis_inline_worker", True):
        session_factory = getattr(request.app.state, "api_session_factory", None)
        if session_factory is None:
            from ..db.session import async_session_factory

            session_factory = async_session_factory
        storage = getattr(request.app.state, "dataset_storage", None) or get_storage()
        background_tasks.add_task(process_queued_analyses, session_factory, storage)
    return _analysis_response(analysis, key.livemode, include_results=False)


@router.get(
    "/analyses/{analysis_id}",
    summary="Get an analysis and, once succeeded, its model results",
    dependencies=[Depends(require_scope("analyses:read"))],
)
async def get_analysis(
    analysis_id: str,
    key=Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    analysis = (
        await session.execute(
            select(Analysis).where(Analysis.id == analysis_id, Analysis.key_id == key.id)
        )
    ).scalar_one_or_none()
    if analysis is None:
        raise _not_found()
    return _analysis_response(analysis, key.livemode)


def _bad_cursor(detail: str) -> ApiProblem:
    return ApiProblem(
        422, "invalid_cursor", "Invalid cursor", detail,
        "Use the next_cursor from the previous page.", "https://docs.rabbit.example/pagination",
    )


@router.get(
    "/analyses",
    summary="List analyses",
    dependencies=[Depends(require_scope("analyses:read"))],
)
async def list_analyses(
    limit: int = 20,
    cursor: str | None = None,
    dataset_id: str | None = None,
    status: str | None = None,
    key=Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    if limit < 1 or limit > 100:
        raise ApiProblem(
            422, "invalid_limit", "Invalid page size", "limit must be between 1 and 100.",
            "Set limit to a value from 1 to 100.", "https://docs.rabbit.example/pagination",
        )
    if status is not None and status not in ANALYSIS_STATUSES:
        raise _invalid(
            "validation_failed",
            f"status must be one of: {', '.join(ANALYSIS_STATUSES)}.",
            "Filter by a valid status.",
        )
    statement = (
        select(Analysis)
        .where(Analysis.key_id == key.id)
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
    )
    if dataset_id:
        statement = statement.where(Analysis.dataset_id == dataset_id)
    if status:
        statement = statement.where(Analysis.status == status)
    if cursor:
        try:
            after_id = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        except Exception as exc:
            raise _bad_cursor("The cursor is malformed.") from exc
        after = await session.get(Analysis, after_id)
        if after is None or after.key_id != key.id:
            raise _bad_cursor("The cursor does not identify an analysis in this scope.")
        statement = statement.where(
            (Analysis.created_at < after.created_at)
            | ((Analysis.created_at == after.created_at) & (Analysis.id < after.id))
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
        "data": [_analysis_response(a, key.livemode, include_results=False) for a in page],
        "next_cursor": next_cursor,
        "has_more": has_more,
    }
