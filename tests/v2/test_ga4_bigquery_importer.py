"""GA4 BigQuery importer: mapping, cost guard and model equivalence.

All BigQuery access is mocked. Rows come from tests/fixtures/ga4/events_rows.json,
hand-built in the GA4 export shape with made-up IDs.
"""

import re
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest

from src.importers import ga4_bigquery as ga4
from src.v2.analyses import compute_model_result, resolve_parameters
from src.v2.datasets import _read_frame, _validation_report
from tests.fixtures.ga4_bigquery import EQUIVALENT_CSV, FakeBigQueryClient, load_rows

ROOT = Path(__file__).resolve().parents[2]
FIVE_MODELS = ["first_touch", "last_touch", "linear", "time_decay", "position_based"]


def _import(client=None, **kwargs):
    client = client or FakeBigQueryClient()
    params = dict(project="demo-project-123", dataset="analytics_123456789",
                  start="20240301", end="20240303", conversion_event="purchase")
    params.update(kwargs)
    return ga4.import_ga4(client=client, **params), client


def _by_key(frame):
    return {(row.customer_id, row.timestamp[:19]): row for row in frame.itertuples()}


# --- mapping -----------------------------------------------------------------


def test_mapping_matches_hand_built_touchpoints():
    result, _ = _import()
    frame = result.frame
    expected = pd.read_csv(EQUIVALENT_CSV, dtype=str, keep_default_na=False)
    assert list(frame.columns) == ga4.TOUCHPOINT_COLUMNS
    assert len(frame) == len(expected) == 11
    got = _by_key(frame)
    for row in expected.itertuples():
        actual = got[(row.customer_id, row.timestamp)]
        assert actual.channel == row.channel
        assert actual.event_type == row.event_type
        assert actual.session_id == row.session_id
        assert (actual.campaign_id or "") == row.campaign_id
        value = actual.conversion_value
        assert ("" if value is None or pd.isna(value) else float(value)) == (
            float(row.conversion_value) if row.conversion_value else "")
    assert result.source_rows == 11
    assert result.stats == {
        "session_starts": 8, "conversions": 3, "skipped_no_identity": 0,
        "skipped_other_event": 0,
        "channel_from_collected_traffic_source": 4,
        "channel_from_session_traffic_source_last_click": 4,
        "channel_from_event_params": 1, "channel_direct": 2,
    }


def test_not_set_and_null_sources_map_to_direct():
    frame, _ = ga4.rows_to_touchpoints(load_rows(), "purchase")
    got = _by_key(frame)
    # (direct)/(none) collected source and (not set) last-click source.
    assert got[("u_madeup_0007", "2024-03-01 12:00:00")].channel == "direct"
    # Both traffic-source records null and no source params.
    assert got[("4000000004.1709310000", "2024-03-01 15:00:00")].channel == "direct"
    for unset in [None, "", "(not set)", "(none)", "(direct)", "  (not set) "]:
        row = {"event_params": [{"key": "source", "value": {"string_value": unset}}]}
        assert ga4.channel_name(*ga4.traffic_source(row)[:2]) == "direct"


def test_channel_fallback_order():
    def row(collected=None, last=None, params=()):
        return {
            "collected_traffic_source": collected,
            "session_traffic_source_last_click": {"manual_campaign": last} if last else None,
            "event_params": [{"key": k, "value": {"string_value": v}} for k, v in params],
        }

    both = row({"manual_source": "google", "manual_medium": "cpc"},
               {"source": "bing", "medium": "cpc"}, [("source", "x"), ("medium", "y")])
    assert ga4.traffic_source(both)[3] == "collected_traffic_source"
    assert ga4.channel_name(*ga4.traffic_source(both)[:2]) == "google / cpc"
    last = row({"manual_source": "(not set)"}, {"source": "bing", "medium": "cpc",
                                                "campaign_name": "brand"})
    assert ga4.traffic_source(last) == ("bing", "cpc", "brand", "session_traffic_source_last_click")
    params = row(None, None, [("source", "Facebook"), ("medium", "Social"), ("campaign", "q1")])
    assert ga4.traffic_source(params) == ("Facebook", "Social", "q1", "event_params")
    assert ga4.channel_name("Facebook", "Social") == "facebook / social"
    assert ga4.channel_name("newsletter", None) == "newsletter"
    # Older exports have no traffic-source columns at all.
    frame, stats = ga4.rows_to_touchpoints(load_rows(), "purchase")
    assert _by_key(frame)[("u_madeup_0007", "2024-03-02 08:00:00")].channel == "facebook / social"
    assert stats["channel_from_event_params"] == 1


def test_conversion_value_prefers_purchase_revenue_then_value_param():
    frame, _ = ga4.rows_to_touchpoints(load_rows(), "purchase")
    got = _by_key(frame)
    # ecommerce.purchase_revenue = 75.0 wins over value param 999.0.
    assert got[("4000000004.1709310000", "2024-03-02 15:10:00")].conversion_value == 75.0
    # purchase_revenue null -> value param 49.99.
    assert got[("u_madeup_0007", "2024-03-03 18:05:00")].conversion_value == 49.99
    assert got[("1000000001.1709280000", "2024-03-02 09:20:00")].conversion_value == 120.5
    int_param = {"ecommerce": None, "event_params": [{"key": "value", "value": {"int_value": 12}}]}
    assert ga4.conversion_value(int_param) == 12.0
    assert ga4.conversion_value({"ecommerce": {"purchase_revenue": -5.0}}) is None
    assert ga4.conversion_value({"ecommerce": None, "event_params": []}) is None
    # Non-conversion touchpoints never carry a value.
    assert frame.loc[frame.event_type == "view", "conversion_value"].isna().all()


def test_user_id_joins_devices_and_falls_back_to_pseudo_id():
    frame, _ = ga4.rows_to_touchpoints(load_rows(), "purchase")
    assert sorted(frame.customer_id.unique()) == [
        "1000000001.1709280000", "4000000004.1709310000",
        "5000000005.1709320000", "u_madeup_0007",
    ]
    assert (frame.customer_id == "u_madeup_0007").sum() == 4


def test_other_events_and_rows_without_identity_are_skipped():
    rows = load_rows() + [
        {"event_timestamp": 1709287300000000, "event_name": "page_view",
         "user_pseudo_id": "1000000001.1709280000", "event_params": []},
        {"event_timestamp": 1709287300000000, "event_name": "session_start",
         "user_pseudo_id": None, "user_id": None, "event_params": []},
    ]
    frame, stats = ga4.rows_to_touchpoints(rows, "purchase")
    assert len(frame) == 11
    assert stats["skipped_other_event"] == 1
    assert stats["skipped_no_identity"] == 1


def test_custom_conversion_event_name():
    rows = [dict(row, event_name="generate_lead") if row["event_name"] == "purchase" else row
            for row in load_rows()]
    frame, stats = ga4.rows_to_touchpoints(rows, "generate_lead")
    assert stats["conversions"] == 3
    frame, stats = ga4.rows_to_touchpoints(rows, "purchase")
    assert stats["conversions"] == 0 and stats["skipped_other_event"] == 3


# --- query, scope and cost guard ----------------------------------------------

FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|DROP|ALTER|TRUNCATE|DECLARE|SET|BEGIN|"
    r"EXECUTE|CALL|EXPORT|LOAD|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


def test_generated_sql_is_a_single_select_with_partition_pruning():
    result, client = _import()
    assert len(client.queries) == 2
    sqls = {q["sql"] for q in client.queries}
    assert len(sqls) == 1, "dry run and real run must send the same statement"
    sql = sqls.pop()
    assert sql.lstrip().upper().startswith("SELECT")
    assert ";" not in sql
    assert not FORBIDDEN.search(sql)
    assert "FROM `demo-project-123.analytics_123456789.events_*`" in sql
    assert "_TABLE_SUFFIX BETWEEN @start AND @end" in sql
    for column in ga4.BASE_COLUMNS + ga4.OPTIONAL_COLUMNS:
        assert column in sql
    assert "SELECT *" not in sql


def test_old_export_without_traffic_source_columns_selects_only_base_columns():
    client = FakeBigQueryClient(columns=ga4.BASE_COLUMNS + ["event_date", "ecommerce"])
    result, client = _import(client)
    sql = client.queries[0]["sql"]
    assert "collected_traffic_source" not in sql
    assert "session_traffic_source_last_click" not in sql
    assert "ecommerce" in sql


def test_dry_run_first_then_query_with_maximum_bytes_billed():
    result, client = _import(max_bytes=123_456_789)
    dry, real = client.queries
    assert dry["job_config"].dry_run is True
    assert real["job_config"].dry_run is not True
    assert real["job_config"].maximum_bytes_billed == 123_456_789
    assert dry["api_method"] == real["api_method"] == "QUERY"  # jobs.query, not jobs.insert
    params = {p.name: p.value for p in real["job_config"].query_parameters}
    assert params == {"start": "20240301", "end": "20240303", "conversion_event": "purchase"}
    assert result.estimated_bytes == 52_428_800


def test_byte_guard_refuses_when_estimate_exceeds_max_bytes():
    client = FakeBigQueryClient(estimated_bytes=11 * 1024**3)
    with pytest.raises(ga4.ByteLimitExceeded) as excinfo:
        _import(client)  # default max_bytes 10 GiB
    assert excinfo.value.estimated == 11 * 1024**3
    assert len(client.queries) == 1 and client.queries[0]["job_config"].dry_run is True


def test_cli_byte_guard_exit_code_and_message(capsys, tmp_path):
    client = FakeBigQueryClient(estimated_bytes=2_000_000)
    out = tmp_path / "t.csv"
    code = ga4.main(["--project", "demo-project-123", "--dataset", "analytics_123456789",
                     "--start", "20240301", "--end", "20240303",
                     "--conversion-event", "purchase", "--max-bytes", "1000000",
                     "--out", str(out)], client=client)
    err = capsys.readouterr().err
    assert code == 3
    assert "Dry run: this query will process 1.91 MiB (2000000 bytes)" in err
    assert "Refused:" in err and "Nothing was queried" in err
    assert not out.exists()
    assert len(client.queries) == 1


def test_cli_writes_touchpoints_and_states_association(capsys, tmp_path):
    out = tmp_path / "touchpoints.csv"
    code = ga4.main(["--project", "demo-project-123", "--dataset", "analytics_123456789",
                     "--start", "20240301", "--end", "20240303",
                     "--conversion-event", "purchase", "--out", str(out)],
                    client=FakeBigQueryClient())
    err = capsys.readouterr().err
    assert code == 0
    assert "Dry run: this query will process 50.00 MiB" in err
    assert "association under the named model, not causal impact" in err
    assert len(pd.read_csv(out)) == 11


def test_start_and_end_are_required(capsys):
    with pytest.raises(SystemExit):
        ga4.main(["--project", "demo-project-123", "--dataset", "a", "--conversion-event", "purchase"])


@pytest.mark.parametrize("kwargs", [
    {"start": "20240305", "end": "20240301"},
    {"start": "2024-03-01"},
    {"end": "20240231"},
    {"dataset": "analytics`; DROP TABLE x; --"},
    {"project": "Bad Project"},
    {"conversion_event": "purchase' OR '1'='1"},
    {"max_bytes": 0},
])
def test_invalid_arguments_are_rejected_before_any_query(kwargs):
    client = FakeBigQueryClient()
    with pytest.raises(ga4.InvalidArgument):
        _import(client, **kwargs)
    assert client.queries == []


def test_no_tables_in_range():
    with pytest.raises(ga4.NoExportTables):
        _import(start="20250101", end="20250131")


def test_make_client_uses_adc_with_read_only_scope():
    assert ga4.SCOPES == ("https://www.googleapis.com/auth/cloud-platform.read-only",)
    creds = object()
    with mock.patch("google.auth.default", return_value=(creds, "adc-project")) as default, \
            mock.patch("google.cloud.bigquery.Client") as client_cls:
        ga4.make_client("billing-project-1")
    default.assert_called_once_with(scopes=["https://www.googleapis.com/auth/cloud-platform.read-only"])
    client_cls.assert_called_once_with(project="billing-project-1", credentials=creds)


# --- equivalence with the CSV upload path --------------------------------------


def _upload_path(content: bytes):
    """What POST /v2/datasets plus an analysis do with an uploaded CSV."""
    frame = _read_frame(content, "csv")
    assert _validation_report(frame).errors == []
    return {
        model: compute_model_result(frame, model, resolve_parameters(model, None))
        for model in FIVE_MODELS
    }


def _assert_same(left, right):
    for model in FIVE_MODELS:
        (l_summary, l_result), (r_summary, r_result) = left[model], right[model]
        assert l_summary == pytest.approx(r_summary)
        assert l_result["parameters"] == r_result["parameters"]
        assert set(l_result["channels"]) == set(r_result["channels"])
        for channel, values in l_result["channels"].items():
            for metric, value in values.items():
                assert value == pytest.approx(r_result["channels"][channel][metric], abs=1e-12), (
                    model, channel, metric)


def test_bigquery_import_gives_same_model_outputs_as_equivalent_csv():
    result, _ = _import()
    from_bigquery = _upload_path(result.frame.to_csv(index=False).encode())
    from_csv = _upload_path(EQUIVALENT_CSV.read_bytes())
    _assert_same(from_bigquery, from_csv)
    summary, _ = from_bigquery["linear"]
    assert summary["total_conversions"] == 3
    assert summary["total_revenue"] == pytest.approx(245.49)
    assert summary["journeys"] == 4
    assert summary["linking_method"] == "customer_id"
    # The models still disagree on this data, which is the point of comparing them.
    first = from_bigquery["first_touch"][1]["channels"]
    last = from_bigquery["last_touch"][1]["channels"]
    assert first != last


# --- the 5 models on test_data.csv are unchanged --------------------------------

TEST_DATA_GOLDEN = {
    "first_touch": {"email": 1 / 3, "organic": 1 / 3, "social": 1 / 3},
    "last_touch": {"email": 2 / 3, "organic": 1 / 3},
    "linear": {"email": 0.3888888888888889, "paid_search": 0.19444444444444445,
               "social": 0.19444444444444445, "organic": 0.22222222222222224},
    "time_decay": {"email": 0.38918585234282926, "paid_search": 0.19455287911145014,
                   "social": 0.1941145316541785, "organic": 0.22214673689154218},
    "position_based": {"email": 0.46666666666666673, "paid_search": 0.09999999999999998,
                       "social": 0.16666666666666666, "organic": 0.26666666666666666},
}


@pytest.mark.parametrize("model", FIVE_MODELS)
def test_five_models_on_test_data_csv_unchanged(model):
    results = _upload_path((ROOT / "test_data.csv").read_bytes())
    summary, result = results[model]
    credits = {channel: values["credit"] for channel, values in result["channels"].items()}
    assert credits == pytest.approx(TEST_DATA_GOLDEN[model], abs=1e-12)
    assert summary["total_conversions"] == 3
    assert summary["total_revenue"] == 225.0
