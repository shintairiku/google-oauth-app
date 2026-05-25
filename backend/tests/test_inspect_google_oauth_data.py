from datetime import date

import httpx

from scripts.inspect_google_oauth_data import (
    build_date_range,
    compact_ga4_report_row,
    compact_search_console_row,
    encode_search_console_site_url,
    extract_error_message,
    flatten_ga4_properties,
)


def test_build_date_range_uses_inclusive_days() -> None:
    start_date, end_date = build_date_range(date(2026, 5, 25), 7)

    assert start_date == date(2026, 5, 19)
    assert end_date == date(2026, 5, 25)


def test_encode_search_console_site_url_escapes_url_for_path_segment() -> None:
    assert encode_search_console_site_url("https://example.com/") == "https%3A%2F%2Fexample.com%2F"
    assert encode_search_console_site_url("sc-domain:example.com") == "sc-domain%3Aexample.com"


def test_flatten_ga4_properties_collects_property_summaries() -> None:
    properties = flatten_ga4_properties(
        [
            {
                "account": "accounts/1",
                "propertySummaries": [
                    {"property": "properties/123", "displayName": "A"},
                    {"property": "properties/456", "displayName": "B"},
                ],
            },
            {"account": "accounts/2", "propertySummaries": "invalid"},
        ]
    )

    assert properties == [
        {"property": "properties/123", "displayName": "A"},
        {"property": "properties/456", "displayName": "B"},
    ]


def test_compact_ga4_report_row_removes_header_noise() -> None:
    row = compact_ga4_report_row(
        {
            "dimensionValues": [{"value": "Japan"}],
            "metricValues": [{"value": "10"}, {"value": "20"}],
        }
    )

    assert row == {"dimensions": ["Japan"], "metrics": ["10", "20"]}


def test_compact_search_console_row_shows_metrics() -> None:
    row = compact_search_console_row(
        {
            "keys": ["example query"],
            "clicks": 12,
            "impressions": 120,
            "ctr": 0.1,
            "position": 3.4,
        }
    )

    assert row == {
        "keys": ["example query"],
        "clicks": 12,
        "impressions": 120,
        "ctr": 0.1,
        "position": 3.4,
    }


def test_extract_error_message_reads_google_error_payload() -> None:
    response = httpx.Response(
        403,
        json={"error": {"message": "API has not been used"}},
    )

    assert extract_error_message(response) == "API has not been used"
