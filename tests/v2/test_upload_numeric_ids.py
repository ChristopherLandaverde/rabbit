"""Numeric-looking identifiers survive the v1 and v2 upload paths (#66).

pandas used to parse ids like 10423, 00123 or 1234567890.1709280000 as numbers;
leading zeros were lost and float customer ids failed the Touchpoint model, so
those rows were dropped without an error.
"""

import asyncio
import io
from pathlib import Path

import pandas as pd
import pytest

from src.v2.analyses import compute_model_result, resolve_parameters
from src.v2.datasets import _read_frame, _validation_report

ROOT = Path(__file__).resolve().parents[2]
FIVE_MODELS = ["first_touch", "last_touch", "linear", "time_decay", "position_based"]


def _upload_path(content: bytes, extension: str = "csv"):
    frame = _read_frame(content, extension)
    assert _validation_report(frame).errors == []
    return {
        model: compute_model_result(frame, model, resolve_parameters(model, None))
        for model in FIVE_MODELS
    }


# --- numeric-looking identifiers survive the upload path (#66) ---------------------

NUMERIC_IDS_CSV = b"""timestamp,channel,event_type,customer_id,session_id,campaign_id,conversion_value
2024-01-01 10:00:00,email,click,10423,1,00042,
2024-01-01 11:00:00,paid_search,click,10423,2,1234567890.1709280000,
2024-01-01 12:00:00,email,conversion,10423,3,00042,50.0
2024-01-02 10:00:00,social,click,00123,4,7,
2024-01-02 11:00:00,email,conversion,00123,5,00042,25.0
2024-01-03 10:00:00,organic,click,1234567890.1709280000,6,8,
2024-01-03 11:00:00,organic,conversion,1234567890.1709280000,7,8,25.0
"""


def test_numeric_ids_keep_every_row_and_leading_zeros():
    frame = _read_frame(NUMERIC_IDS_CSV, "csv")
    assert frame.customer_id.tolist()[3] == "00123"
    assert frame.customer_id.tolist()[5] == "1234567890.1709280000"
    assert frame.campaign_id.tolist()[:2] == ["00042", "1234567890.1709280000"]
    results = _upload_path(NUMERIC_IDS_CSV)
    summary, result = results["linear"]
    assert summary["touchpoints"] == 7
    assert summary["journeys"] == 3
    assert summary["total_conversions"] == 3
    assert summary["total_revenue"] == 100.0
    # first_touch: one conversion each for email, social, organic.
    first = results["first_touch"][1]["channels"]
    assert {c: v["credit"] for c, v in first.items()} == pytest.approx(
        {"email": 1 / 3, "social": 1 / 3, "organic": 1 / 3})


def test_numeric_ids_in_json_and_parquet_stay_text(tmp_path):
    rows = pd.read_csv(io.BytesIO(NUMERIC_IDS_CSV), dtype=str)
    as_json_lines = rows.to_json(orient="records", lines=True).encode()
    frame = _read_frame(as_json_lines, "json")
    assert frame.customer_id.tolist()[3] == "00123"
    assert frame.campaign_id.tolist()[0] == "00042"
    numeric = rows.assign(customer_id=[10423, 10423, 10423, 123, 123, 9, 9])
    path = tmp_path / "ids.parquet"
    numeric.to_parquet(path)
    frame = _read_frame(path.read_bytes(), "parquet")
    assert frame.customer_id.tolist()[0] == "10423"
    assert _upload_path(as_json_lines, "json")["linear"][0]["touchpoints"] == 7


def test_upload_validation_reports_rows_that_will_be_dropped():
    from src.v2.datasets import _dropped_row_warnings

    assert _dropped_row_warnings(_read_frame(NUMERIC_IDS_CSV, "csv")) == []
    assert _dropped_row_warnings(_read_frame((ROOT / "test_data.csv").read_bytes(), "csv")) == []
    bad = NUMERIC_IDS_CSV.replace(b"50.0", b"-50.0")  # negative value fails the Touchpoint model
    warnings = _dropped_row_warnings(_read_frame(bad, "csv"))
    assert len(warnings) == 1 and warnings[0].code == "rows_dropped"
    assert warnings[0].message.startswith("1 of 7 rows cannot become touchpoints")


def test_v1_analyze_reports_rows_dropped():
    from src.core.attribution_service import AttributionService
    from src.models.enums import AttributionModelType

    async def run(content):
        frame = _read_frame(content, "csv")
        frame["timestamp"] = pd.to_datetime(frame["timestamp"])
        response = await AttributionService().analyze_attribution(frame, AttributionModelType.LINEAR)
        return response.metadata.rows_dropped

    assert asyncio.run(run(NUMERIC_IDS_CSV)) == 0
    assert asyncio.run(run((ROOT / "test_data.csv").read_bytes())) == 0
    assert asyncio.run(run(NUMERIC_IDS_CSV.replace(b"50.0", b"-50.0"))) == 1


def test_dropped_row_reasons_are_collected_without_touching_stdout(capsys, monkeypatch):
    """The upload check gets drop reasons from the builder, not by redirecting
    process-wide stdout (which races across threads)."""
    import contextlib

    from src.core.identity.journey_builder import JourneyBuilder
    from src.v2.datasets import _dropped_row_warnings

    def no_redirect(*args, **kwargs):
        raise AssertionError("redirect_stdout must not be used")

    monkeypatch.setattr(contextlib, "redirect_stdout", no_redirect)
    bad = _read_frame(NUMERIC_IDS_CSV.replace(b"50.0", b"-50.0"), "csv")
    warnings = _dropped_row_warnings(bad)
    assert capsys.readouterr().out == ""
    assert len(warnings) == 1
    assert "First reason: Error creating touchpoint at index" in warnings[0].message
    assert warnings[0].message.endswith("1 validation error for Touchpoint")

    # Without an errors list the builder still prints, as the models expect.
    frame = bad.copy()
    frame["timestamp"] = __import__("pandas").to_datetime(frame["timestamp"])
    JourneyBuilder()._create_touchpoints(frame)
    assert "Error creating touchpoint" in capsys.readouterr().out
