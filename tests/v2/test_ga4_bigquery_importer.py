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
                  start="20250301", end="20250315", conversion_event="purchase")
    params.update(kwargs)
    return ga4.import_ga4(client=client, **params), client


def _by_key(frame):
    return {(row.customer_id, row.timestamp[:19], row.event_type): row for row in frame.itertuples()}


# --- mapping -----------------------------------------------------------------


def test_mapping_matches_hand_built_touchpoints():
    result, _ = _import()
    frame = result.frame
    expected = pd.read_csv(EQUIVALENT_CSV, dtype=str, keep_default_na=False)
    assert list(frame.columns) == ga4.TOUCHPOINT_COLUMNS
    assert len(frame) == len(expected) == 16
    got = _by_key(frame)
    for row in expected.itertuples():
        actual = got[(row.customer_id, row.timestamp, row.event_type)]
        assert actual.channel == row.channel, row
        assert actual.session_id == row.session_id
        assert (actual.campaign_id or "") == row.campaign_id, row
        value = actual.conversion_value
        assert ("" if value is None or pd.isna(value) else float(value)) == (
            float(row.conversion_value) if row.conversion_value else "")
    assert result.source_rows == 16
    assert result.stats == {
        "session_starts": 12, "conversions": 4, "skipped_no_identity": 0,
        "skipped_other_event": 0,
        "channel_from_collected_utm": 5,
        "channel_from_collected_gclid": 2,
        "channel_from_last_non_direct_click": 7,
        "channel_from_event_params": 0,
        "channel_direct": 2,
    }


def _mapped():
    frame, _ = ga4.rows_to_touchpoints(load_rows(), "purchase")
    return _by_key(frame)


def test_not_set_and_null_sources_map_to_direct():
    got = _mapped()
    # Last click (direct)/(none): a first visit with no earlier source.
    assert got[("user:u_madeup_0007", "2025-03-01 12:00:00", "view")].channel == "direct"
    # Last click (not set)/(not set).
    assert got[("ga4:7000000007.1709340000", "2025-03-02 20:00:00", "view")].channel == "direct"
    for unset in [None, "", "(not set)", "(none)", "(direct)", "  (not set) "]:
        row = {"collected_traffic_source": {"manual_source": unset},
               "session_traffic_source_last_click": {"cross_channel_campaign": {"source": unset}}}
        assert ga4.traffic_source(row) == (None, None, None, "direct")
        old = {"event_params": [{"key": "source", "value": {"string_value": unset}}]}
        assert ga4.channel_name(*ga4.traffic_source(old)[:2]) == "direct"


def test_untagged_sessions_follow_ga4_last_non_direct_click():
    got = _mapped()
    # Untagged organic: nothing collected, source from last click.
    assert got[("ga4:4000000004.1709310000", "2025-03-01 15:00:00", "view")].channel == "google / organic"
    # Direct return visit inherits the earlier source, as in GA4's session source.
    assert got[("ga4:4000000004.1709310000", "2025-03-02 15:00:00", "view")].channel == "google / organic"
    assert got[("ga4:6000000006.1709330000", "2025-03-08 00:00:00", "view")].channel == "newsletter / email"


def test_gclid_only_session_is_google_cpc_with_ads_campaign():
    got = _mapped()
    touch = got[("ga4:5000000005.1709320000", "2025-03-03 11:00:00", "view")]
    assert (touch.channel, touch.campaign_id) == ("google / cpc", "brand_search")
    bare = {"collected_traffic_source": {"gclid": "x"}, "session_traffic_source_last_click": None}
    assert ga4.traffic_source(bare) == ("google", "cpc", None, "collected_gclid")


def test_channel_precedence():
    def row(collected=None, last=None, params=()):
        return {
            "collected_traffic_source": collected,
            "session_traffic_source_last_click": last,
            "event_params": [{"key": k, "value": {"string_value": v}} for k, v in params],
        }

    last = {"cross_channel_campaign": {"source": "bing", "medium": "cpc", "campaign_name": "brand"},
            "google_ads_campaign": {"campaign_name": "ads_campaign"}}
    params = [("source", "x"), ("medium", "y")]
    # UTM beats gclid, last click and params.
    utm = row({"manual_source": "Newsletter", "manual_medium": "Email", "gclid": "g"}, last, params)
    assert ga4.traffic_source(utm)[3] == "collected_utm"
    assert ga4.channel_name(*ga4.traffic_source(utm)[:2]) == "newsletter / email"
    # gclid beats last click.
    assert ga4.traffic_source(row({"gclid": "g"}, last, params)) == (
        "google", "cpc", "ads_campaign", "collected_gclid")
    # Last click beats params; a present last-click record with no source is direct.
    assert ga4.traffic_source(row(None, last, params)) == ("bing", "cpc", "brand", "last_non_direct_click")
    assert ga4.traffic_source(row(None, {"cross_channel_campaign": None}, params))[3] == "direct"
    # Params only when the row has no last-click record (exported before July 2024).
    assert ga4.traffic_source(row(None, None, [("source", "Facebook"), ("medium", "Social"),
                                               ("campaign", "q1")])) == (
        "Facebook", "Social", "q1", "event_params")
    assert ga4.channel_name("newsletter", None) == "newsletter"
    got = _mapped()
    assert got[("user:u_madeup_0007", "2025-03-02 08:00:00", "view")].channel == "facebook / social"
    # A present last-click record with no cross-channel source falls back to
    # manual_campaign, then google_ads_campaign (July-October 2024 exports).
    manual = {"cross_channel_campaign": None,
              "manual_campaign": {"source": "newsletter", "medium": "email", "campaign_name": "n"},
              "google_ads_campaign": {"campaign_name": "ads"}}
    assert ga4.traffic_source(row(None, manual, params)) == (
        "newsletter", "email", "n", "last_non_direct_click")
    ads_only = {"cross_channel_campaign": None, "manual_campaign": {"source": "(not set)"},
                "google_ads_campaign": {"campaign_id": "111", "campaign_name": "ads"}}
    assert ga4.traffic_source(row(None, ads_only, params)) == (
        "google", "cpc", "ads", "last_non_direct_click")


def test_conversion_value_prefers_usd_then_revenue_then_value_param():
    got = _mapped()
    # purchase_revenue_in_usd 81.0 beats purchase_revenue 75.0 (EUR) and value 75.0.
    assert got[("ga4:4000000004.1709310000", "2025-03-02 15:10:00", "conversion")].conversion_value == 81.0
    # No ecommerce revenue -> value param 49.99.
    assert got[("user:u_madeup_0007", "2025-03-03 18:05:00", "conversion")].conversion_value == 49.99
    assert got[("ga4:1000000001.1709280000", "2025-03-02 09:20:00", "conversion")].conversion_value == 120.5
    assert ga4.conversion_value({"ecommerce": {"purchase_revenue": 7.5}}) == 7.5
    int_param = {"ecommerce": None, "event_params": [{"key": "value", "value": {"int_value": 12}}]}
    assert ga4.conversion_value(int_param) == 12.0
    assert ga4.conversion_value({"ecommerce": {"purchase_revenue_in_usd": -5.0}}) is None
    assert ga4.conversion_value({"ecommerce": None, "event_params": []}) is None
    frame, _ = ga4.rows_to_touchpoints(load_rows(), "purchase")
    assert frame.loc[frame.event_type == "view", "conversion_value"].isna().all()


def test_user_id_joins_devices_and_falls_back_to_pseudo_id():
    frame, _ = ga4.rows_to_touchpoints(load_rows(), "purchase")
    assert sorted(frame.customer_id.unique()) == [
        "ga4:1000000001.1709280000", "ga4:4000000004.1709310000", "ga4:5000000005.1709320000",
        "ga4:6000000006.1709330000", "ga4:7000000007.1709340000", "user:u_madeup_0007",
    ]
    # Both devices, including B1's row from before login.
    assert (frame.customer_id == "user:u_madeup_0007").sum() == 4


def test_other_events_and_consent_denied_rows_are_skipped():
    rows = load_rows() + [
        {"event_timestamp": 1709287300000000, "event_name": "page_view",
         "user_pseudo_id": "1000000001.1709280000", "event_params": []},
        # Consent mode denied: cookieless ping with no user_pseudo_id.
        {"event_timestamp": 1709287300000000, "event_name": "session_start",
         "user_pseudo_id": None, "user_id": None, "event_params": []},
    ]
    frame, stats = ga4.rows_to_touchpoints(rows, "purchase")
    assert len(frame) == 16
    assert stats["skipped_other_event"] == 1
    assert stats["skipped_no_identity"] == 1


def test_custom_conversion_event_name():
    rows = [dict(row, event_name="generate_lead") if row["event_name"] == "purchase" else row
            for row in load_rows()]
    frame, stats = ga4.rows_to_touchpoints(rows, "generate_lead")
    assert stats["conversions"] == 4
    frame, stats = ga4.rows_to_touchpoints(rows, "purchase")
    assert stats["conversions"] == 0 and stats["skipped_other_event"] == 4


# --- query, scope and cost guard ----------------------------------------------

FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|DROP|ALTER|TRUNCATE|DECLARE|SET|BEGIN|"
    r"EXECUTE|CALL|EXPORT|LOAD|GRANT|REVOKE)\b",
    re.IGNORECASE,
)
CLI_ARGS = ["--project", "demo-project-123", "--dataset", "analytics_123456789",
            "--start", "20250301", "--end", "20250315", "--conversion-event", "purchase"]


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


def test_schema_comes_from_newest_table_matching_the_wildcard():
    _, client = _import(end="20250302")
    # Newest matching table is the intraday one, outside the requested range.
    assert client.schema_reads == ["demo-project-123.analytics_123456789.events_intraday_20250315"]


def test_old_export_without_traffic_source_columns_selects_only_base_columns():
    client = FakeBigQueryClient(columns=ga4.BASE_COLUMNS + ["event_date", "ecommerce"])
    result, client = _import(client)
    sql = client.queries[0]["sql"]
    assert "collected_traffic_source" not in sql
    assert "session_traffic_source_last_click" not in sql
    assert "ecommerce" in sql
    # Without last-click records, sessions fall back to event params or direct.
    assert result.stats["channel_from_last_non_direct_click"] == 0
    assert result.stats["channel_from_event_params"] == 1


def test_dry_run_first_then_query_with_maximum_bytes_billed():
    result, client = _import(max_bytes=123_456_789)
    dry, real = client.queries
    assert dry["job_config"].dry_run is True
    assert real["job_config"].dry_run is not True
    assert real["job_config"].maximum_bytes_billed == 123_456_789
    assert dry["api_method"] == real["api_method"] == "QUERY"  # jobs.query, not jobs.insert
    params = {p.name: p.value for p in real["job_config"].query_parameters}
    assert params == {"start": "20250301", "end": "20250315", "conversion_event": "purchase"}
    assert result.estimated_bytes == 52_428_800


def test_byte_guard_refuses_when_estimate_exceeds_max_bytes():
    client = FakeBigQueryClient(estimated_bytes=11 * 1024**3)
    with pytest.raises(ga4.ByteLimitExceeded) as excinfo:
        _import(client)  # default max_bytes 10 GiB
    assert excinfo.value.estimated == 11 * 1024**3
    assert len(client.queries) == 1 and client.queries[0]["job_config"].dry_run is True


def test_dry_run_without_estimate_is_an_error_not_zero(capsys):
    client = FakeBigQueryClient(estimated_bytes=None)
    with pytest.raises(ga4.BigQueryFailed):
        _import(client)
    assert len(client.queries) == 1
    assert ga4.main(CLI_ARGS, client=FakeBigQueryClient(estimated_bytes=None)) == 6
    assert "no bytes estimate" in capsys.readouterr().err


def test_cli_byte_guard_exit_code_and_message(capsys, tmp_path):
    client = FakeBigQueryClient(estimated_bytes=2_000_000)
    out = tmp_path / "t.csv"
    code = ga4.main(CLI_ARGS + ["--max-bytes", "1000000", "--out", str(out)], client=client)
    err = capsys.readouterr().err
    assert code == 3
    assert "Dry run: this query will process 1.91 MiB (2000000 bytes) from 5 daily tables" in err
    assert "Refused:" in err and "Nothing was queried" in err
    assert not out.exists()
    assert len(client.queries) == 1


def test_bytes_billed_rejection_maps_to_exit_4(capsys):
    from google.api_core.exceptions import BadRequest

    error = BadRequest("Query exceeded limit for bytes billed: 1000000. 20971520 or higher required.",
                       errors=[{"reason": "bytesBilledLimitExceeded"}])
    client = FakeBigQueryClient(estimated_bytes=10, query_error=error)
    with pytest.raises(ga4.BytesBilledExceeded):
        _import(client)
    code = ga4.main(CLI_ARGS, client=FakeBigQueryClient(estimated_bytes=10, query_error=error))
    assert code == 4
    assert "would bill more than --max-bytes" in capsys.readouterr().err


@pytest.mark.parametrize("error_name, exit_code", [
    ("Forbidden", 5), ("Unauthorized", 5), ("NotFound", 2), ("InternalServerError", 6),
])
def test_bigquery_errors_map_to_exit_codes(error_name, exit_code, capsys):
    from google.api_core import exceptions

    error = getattr(exceptions, error_name)("made-up failure")
    code = ga4.main(CLI_ARGS, client=FakeBigQueryClient(query_error=error))
    assert code == exit_code
    assert "made-up failure" in capsys.readouterr().err


def test_missing_adc_maps_to_access_denied():
    from google.auth.exceptions import DefaultCredentialsError

    with mock.patch("google.auth.default", side_effect=DefaultCredentialsError("none")):
        with pytest.raises(ga4.AccessDenied) as excinfo:
            ga4.make_client("billing-project-1")
    assert "gcloud auth application-default login" in str(excinfo.value)


def test_cli_writes_touchpoints_and_states_meaning(capsys, tmp_path):
    out = tmp_path / "touchpoints.csv"
    code = ga4.main(CLI_ARGS + ["--out", str(out)], client=FakeBigQueryClient())
    err = capsys.readouterr().err
    assert code == 0
    assert "Dry run: this query will process 50.00 MiB" in err
    assert "at least 10 MB per table" in err
    assert "0 rows skipped with no user id" in err
    assert "last non-direct session source" in err and "direct is undercounted" in err
    assert "association under the named model, not causal impact" in err
    assert len(pd.read_csv(out)) == 16


def test_start_and_end_are_required(capsys):
    with pytest.raises(SystemExit):
        ga4.main(["--project", "demo-project-123", "--dataset", "a", "--conversion-event", "purchase"])


@pytest.mark.parametrize("kwargs", [
    {"start": "20240305", "end": "20240301"},
    {"start": "2025-03-01"},
    {"end": "20240231"},
    {"start": "20250301\n"},
    {"dataset": "analytics`; DROP TABLE x; --"},
    {"dataset": "analytics_1\n"},
    {"project": "Bad Project"},
    {"project": "demo-project-123\n"},
    {"conversion_event": "purchase' OR '1'='1"},
    {"conversion_event": "session_start"},
    {"max_bytes": 0},
])
def test_invalid_arguments_are_rejected_before_any_query(kwargs):
    client = FakeBigQueryClient()
    with pytest.raises(ga4.InvalidArgument):
        _import(client, **kwargs)
    assert client.queries == []


def test_no_tables_in_range():
    with pytest.raises(ga4.NoExportTables):
        _import(start="20260101", end="20260131")


def test_make_client_uses_adc_with_read_only_scope():
    assert ga4.SCOPES == ("https://www.googleapis.com/auth/cloud-platform.read-only",)
    creds = object()
    with mock.patch("google.auth.default", return_value=(creds, "adc-project")) as default, \
            mock.patch("google.cloud.bigquery.Client") as client_cls:
        ga4.make_client("billing-project-1")
        ga4.make_client("billing-project-1", ga4.BIGQUERY_READONLY)
    assert default.call_args_list == [
        mock.call(scopes=["https://www.googleapis.com/auth/cloud-platform.read-only"]),
        mock.call(scopes=["https://www.googleapis.com/auth/bigquery.readonly"]),
    ]
    client_cls.assert_called_with(project="billing-project-1", credentials=creds)
    with pytest.raises(ga4.InvalidArgument):
        ga4.make_client("billing-project-1", "https://www.googleapis.com/auth/bigquery")


# --- equivalence with the CSV upload path --------------------------------------


def _upload_path(content: bytes, extension: str = "csv"):
    """What POST /v2/datasets plus an analysis do with an uploaded file."""
    frame = _read_frame(content, extension)
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


def test_fake_client_returns_real_bigquery_rows():
    from google.cloud.bigquery.table import Row

    _, client = _import()
    rows = list(client.query(client.queries[-1]["sql"], job_config=client.queries[-1]["job_config"],
                             api_method="QUERY").result())
    assert rows and all(isinstance(row, Row) for row in rows)
    assert set(rows[0].keys()) == set(ga4.BASE_COLUMNS + ga4.OPTIONAL_COLUMNS)


def test_bigquery_import_gives_same_model_outputs_as_equivalent_csv():
    result, _ = _import()
    from_bigquery = _upload_path(result.frame.to_csv(index=False).encode())
    from_csv = _upload_path(EQUIVALENT_CSV.read_bytes())
    _assert_same(from_bigquery, from_csv)
    summary, _ = from_bigquery["linear"]
    assert summary["total_conversions"] == 4
    assert summary["total_revenue"] == pytest.approx(120.5 + 49.99 + 81.0 + 100.0)
    assert summary["journeys"] == 6
    assert summary["linking_method"] == "customer_id"
    first = from_bigquery["first_touch"][1]["channels"]
    last = from_bigquery["last_touch"][1]["channels"]
    assert first != last


# Journey 6000000006: email UTM (Mar 1), direct return that inherits email via
# last click (Mar 8), gclid session (Mar 15 00:00) and purchase of $100 in that
# session at the same instant. Channels: email, email, google / cpc, google / cpc.
#   first_touch:    email 1
#   last_touch:     google / cpc 1
#   linear:         4 touches x 1/4 -> email 1/2, cpc 1/2
#   position_based: first 0.4 email, last 0.4 cpc, two middle touches share
#                   0.2 -> 0.1 email + 0.1 cpc -> email 1/2, cpc 1/2
#   time_decay:     half-life 7 days; ages 14, 7, 0, 0 days -> weights
#                   1/4, 1/2, 1, 1 (sum 11/4) -> email 3/11, cpc 8/11
HAND_CALCULATED = {
    "first_touch": {"newsletter / email": 1.0},
    "last_touch": {"google / cpc": 1.0},
    "linear": {"newsletter / email": 0.5, "google / cpc": 0.5},
    "position_based": {"newsletter / email": 0.5, "google / cpc": 0.5},
    "time_decay": {"newsletter / email": 3 / 11, "google / cpc": 8 / 11},
}


@pytest.mark.parametrize("model", FIVE_MODELS)
def test_hand_calculated_journey_through_bigquery_import(model):
    # Only numeric-looking pseudo ids here: without the "ga4:" prefix the CSV
    # would parse customer_id as a float and every touchpoint would be dropped.
    rows = [row for row in load_rows() if row["user_pseudo_id"] == "6000000006.1709330000"]
    result, _ = _import(FakeBigQueryClient(rows=rows))
    summary, outcome = _upload_path(result.frame.to_csv(index=False).encode())[model]
    credits = {channel: values["credit"] for channel, values in outcome["channels"].items()}
    expected = {channel: value for channel, value in HAND_CALCULATED[model].items()}
    credits = {channel: value for channel, value in credits.items() if value}
    assert credits == pytest.approx(expected, abs=1e-12)
    revenue = {channel: values["revenue"] for channel, values in outcome["channels"].items()}
    for channel, share in expected.items():
        assert revenue[channel] == pytest.approx(100.0 * share, abs=1e-9)
    assert summary["total_revenue"] == 100.0


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


# --- exports across the July / October 2024 schema changes ---------------------

TRANSITION_ROWS = Path(__file__).resolve().parents[1] / "fixtures" / "ga4" / "events_rows_2024_transition.json"


def test_july_to_october_2024_rows_use_manual_and_ads_last_click():
    import json

    rows = json.loads(TRANSITION_ROWS.read_text())
    client = FakeBigQueryClient(rows=rows, days=("20240620", "20240810", "20240811",
                                                  "20240812", "20241102"))
    result, _ = _import(client, start="20240620", end="20241102")
    channels = list(zip(result.frame.timestamp.str[:10], result.frame.event_type,
                        result.frame.channel, result.frame.campaign_id))
    assert channels == [
        ("2024-06-20", "view", "google / organic", None),          # event params
        ("2024-08-10", "view", "newsletter / email", "aug_news"),  # last click manual_campaign
        ("2024-08-11", "view", "google / cpc", "brand_search"),    # last click google_ads_campaign
        ("2024-08-12", "view", "direct", None),                    # (direct) / (none)
        ("2024-08-12", "conversion", "direct", None),
        ("2024-11-02", "view", "google / organic", None),          # cross_channel_campaign
    ]
    assert result.stats["channel_from_event_params"] == 1
    assert result.stats["channel_from_last_non_direct_click"] == 3
    assert result.stats["channel_direct"] == 2
    assert result.frame.conversion_value.dropna().tolist() == [30.0]


# --- credential and response errors ----------------------------------------------


def test_refresh_error_maps_to_exit_5(capsys):
    from google.auth.exceptions import RefreshError

    code = ga4.main(CLI_ARGS, client=FakeBigQueryClient(query_error=RefreshError("token expired")))
    assert code == 5
    err = capsys.readouterr().err
    assert "RefreshError" in err and "application-default login" in err


def test_dry_run_response_without_job_reference_maps_to_exit_6(capsys):
    class NoJobReference(FakeBigQueryClient):
        def query(self, sql, job_config=None, api_method="INSERT", **kwargs):
            if job_config is not None and job_config.dry_run:
                self.queries.append({"sql": sql, "job_config": job_config, "api_method": api_method})
                raise KeyError("jobReference")
            return super().query(sql, job_config, api_method, **kwargs)

    client = NoJobReference()
    assert ga4.main(CLI_ARGS, client=client) == 6
    assert "no jobReference field" in capsys.readouterr().err
    assert len(client.queries) == 1
