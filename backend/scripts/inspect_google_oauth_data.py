import argparse
import asyncio
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.services.token_cipher import TokenCipher

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GA4_ACCOUNT_SUMMARIES_URL = "https://analyticsadmin.googleapis.com/v1beta/accountSummaries"
SEARCH_CONSOLE_SITES_URL = "https://www.googleapis.com/webmasters/v3/sites"


def default_end_date() -> date:
    return datetime.now(UTC).date() - timedelta(days=1)


def build_date_range(end_date: date, days: int) -> tuple[date, date]:
    if days < 1:
        raise ValueError("days must be greater than or equal to 1")
    return end_date - timedelta(days=days - 1), end_date


def encode_search_console_site_url(site_url: str) -> str:
    return quote(site_url, safe="")


async def main() -> None:
    args = parse_args()
    start_date, end_date = build_date_range(args.end_date, args.days)

    encrypted_refresh_token = settings.require_google_oauth_encrypted_refresh_token()
    refresh_token = TokenCipher(settings.require_token_encryption_key()).decrypt(
        encrypted_refresh_token
    )

    async with httpx.AsyncClient(timeout=args.timeout) as client:
        access_token = await refresh_access_token(client, refresh_token)
        headers = {"Authorization": f"Bearer {access_token}"}

        result = {
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "search_console": await inspect_search_console(
                client=client,
                headers=headers,
                start_date=start_date,
                end_date=end_date,
                max_sites=args.max_sites,
                row_limit=args.row_limit,
            ),
            "ga4": await inspect_ga4(
                client=client,
                headers=headers,
                start_date=start_date,
                end_date=end_date,
                max_properties=args.max_properties,
                row_limit=args.row_limit,
            ),
        }

    print_summary(result)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nJSON output: {args.output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="暗号化済みrefresh tokenでGA4 / Search Consoleのサンプルデータを取得する"
    )
    parser.add_argument("--days", type=int, default=28, help="取得対象日数。初期値は28日")
    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        default=default_end_date(),
        help="取得終了日。YYYY-MM-DD形式。初期値はUTC基準の昨日",
    )
    parser.add_argument("--max-sites", type=int, default=10, help="Search Console取得サイト数")
    parser.add_argument("--max-properties", type=int, default=10, help="GA4取得プロパティ数")
    parser.add_argument("--row-limit", type=int, default=20, help="各レポートの最大行数")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="結果JSONの保存先。例: tmp/google_oauth_data_sample.json",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="Google APIのtimeout秒数")
    return parser.parse_args()


async def refresh_access_token(client: httpx.AsyncClient, refresh_token: str) -> str:
    data = {
        "client_id": settings.require_google_oauth_client_id(),
        "client_secret": settings.require_google_oauth_client_secret(),
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    response = await client.post(GOOGLE_TOKEN_URL, data=data)
    if response.is_error:
        raise RuntimeError(f"access token refresh failed: {extract_error_message(response)}")

    access_token = response.json().get("access_token")
    if not access_token:
        raise RuntimeError("access_token was not returned")
    return str(access_token)


async def inspect_search_console(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    start_date: date,
    end_date: date,
    max_sites: int,
    row_limit: int,
) -> dict[str, Any]:
    response = await client.get(SEARCH_CONSOLE_SITES_URL, headers=headers)
    if response.is_error:
        return {"error": extract_error_payload(response), "sites": []}

    sites = response.json().get("siteEntry", [])
    if not isinstance(sites, list):
        sites = []

    inspected_sites = []
    for site in sites[:max_sites]:
        site_url = str(site.get("siteUrl", ""))
        if not site_url:
            continue
        inspected_sites.append(
            {
                "site_url": site_url,
                "permission_level": site.get("permissionLevel"),
                "reports": {
                    "top_queries": await query_search_console(
                        client,
                        headers,
                        site_url,
                        start_date,
                        end_date,
                        ["query"],
                        row_limit,
                    ),
                    "top_pages": await query_search_console(
                        client,
                        headers,
                        site_url,
                        start_date,
                        end_date,
                        ["page"],
                        row_limit,
                    ),
                    "daily": await query_search_console(
                        client,
                        headers,
                        site_url,
                        start_date,
                        end_date,
                        ["date"],
                        row_limit,
                    ),
                },
            }
        )

    return {"site_count": len(sites), "sites": inspected_sites}


async def query_search_console(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    site_url: str,
    start_date: date,
    end_date: date,
    dimensions: list[str],
    row_limit: int,
) -> dict[str, Any]:
    encoded_site_url = encode_search_console_site_url(site_url)
    url = (
        "https://www.googleapis.com/webmasters/v3/sites/"
        f"{encoded_site_url}/searchAnalytics/query"
    )
    payload = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "dimensions": dimensions,
        "rowLimit": row_limit,
    }
    response = await client.post(url, headers=headers, json=payload)
    if response.is_error:
        return {"error": extract_error_payload(response), "rows": []}
    return {"rows": response.json().get("rows", [])}


async def inspect_ga4(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    start_date: date,
    end_date: date,
    max_properties: int,
    row_limit: int,
) -> dict[str, Any]:
    account_summaries = await list_ga4_account_summaries(client, headers)
    properties = flatten_ga4_properties(account_summaries)

    inspected_properties = []
    for property_summary in properties[:max_properties]:
        property_name = str(property_summary.get("property", ""))
        if not property_name:
            continue
        inspected_properties.append(
            {
                "property": property_name,
                "display_name": property_summary.get("displayName"),
                "property_type": property_summary.get("propertyType"),
                "reports": {
                    "daily": await run_ga4_report(
                        client,
                        headers,
                        property_name,
                        start_date,
                        end_date,
                        dimensions=["date"],
                        metrics=["activeUsers", "sessions", "screenPageViews", "eventCount"],
                        row_limit=row_limit,
                    ),
                    "country": await run_ga4_report(
                        client,
                        headers,
                        property_name,
                        start_date,
                        end_date,
                        dimensions=["country"],
                        metrics=["activeUsers", "sessions"],
                        row_limit=row_limit,
                    ),
                    "device": await run_ga4_report(
                        client,
                        headers,
                        property_name,
                        start_date,
                        end_date,
                        dimensions=["deviceCategory"],
                        metrics=["activeUsers", "sessions"],
                        row_limit=row_limit,
                    ),
                },
            }
        )

    return {
        "account_summary_count": len(account_summaries),
        "property_count": len(properties),
        "properties": inspected_properties,
    }


async def list_ga4_account_summaries(
    client: httpx.AsyncClient,
    headers: dict[str, str],
) -> list[dict[str, Any]]:
    account_summaries: list[dict[str, Any]] = []
    page_token: str | None = None

    while True:
        params = {"pageSize": "200"}
        if page_token:
            params["pageToken"] = page_token
        response = await client.get(GA4_ACCOUNT_SUMMARIES_URL, headers=headers, params=params)
        if response.is_error:
            raise RuntimeError(f"GA4 accountSummaries failed: {extract_error_message(response)}")

        payload = response.json()
        items = payload.get("accountSummaries", [])
        if isinstance(items, list):
            account_summaries.extend(items)

        page_token = payload.get("nextPageToken")
        if not page_token:
            return account_summaries


def flatten_ga4_properties(account_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    properties: list[dict[str, Any]] = []
    for account_summary in account_summaries:
        property_summaries = account_summary.get("propertySummaries", [])
        if isinstance(property_summaries, list):
            properties.extend(
                property_summary
                for property_summary in property_summaries
                if isinstance(property_summary, dict)
            )
    return properties


async def run_ga4_report(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    property_name: str,
    start_date: date,
    end_date: date,
    dimensions: list[str],
    metrics: list[str],
    row_limit: int,
) -> dict[str, Any]:
    url = f"https://analyticsdata.googleapis.com/v1beta/{property_name}:runReport"
    payload = {
        "dateRanges": [
            {"startDate": start_date.isoformat(), "endDate": end_date.isoformat()},
        ],
        "dimensions": [{"name": dimension} for dimension in dimensions],
        "metrics": [{"name": metric} for metric in metrics],
        "limit": str(row_limit),
    }
    response = await client.post(url, headers=headers, json=payload)
    if response.is_error:
        return {"error": extract_error_payload(response), "rows": []}
    return {"rows": response.json().get("rows", [])}


def print_summary(result: dict[str, Any]) -> None:
    date_range = result["date_range"]
    print(f"Date range: {date_range['start_date']} to {date_range['end_date']}")

    search_console = result["search_console"]
    if search_console.get("error"):
        print(f"\nNG: Search Console sites: {search_console['error']['message']}")
    else:
        print(f"\nOK: Search Console sites: {search_console['site_count']} items")
        for site in search_console["sites"]:
            print(f"- {site['site_url']} ({site.get('permission_level')})")
            for report_name, report in site["reports"].items():
                print_report_rows(f"  {report_name}", report)

    ga4 = result["ga4"]
    print(
        "\nOK: GA4 account summaries: "
        f"{ga4['account_summary_count']} accounts, {ga4['property_count']} properties"
    )
    for property_result in ga4["properties"]:
        print(f"- {property_result['property']} {property_result.get('display_name') or ''}")
        for report_name, report in property_result["reports"].items():
            print_report_rows(f"  {report_name}", report)


def print_report_rows(label: str, report: dict[str, Any]) -> None:
    if report.get("error"):
        print(f"{label}: NG {report['error']['status_code']} {report['error']['message']}")
        return

    rows = report.get("rows", [])
    row_count = len(rows) if isinstance(rows, list) else 0
    print(f"{label}: {row_count} rows")
    for row in rows[:3]:
        print(f"    {compact_report_row(row)}")


def compact_report_row(row: dict[str, Any]) -> dict[str, Any]:
    if "keys" in row:
        return compact_search_console_row(row)
    return compact_ga4_report_row(row)


def compact_search_console_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "keys": [str(value) for value in row.get("keys", [])],
        "clicks": row.get("clicks"),
        "impressions": row.get("impressions"),
        "ctr": row.get("ctr"),
        "position": row.get("position"),
    }


def compact_ga4_report_row(row: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "dimensions": [
            str(value.get("value", ""))
            for value in row.get("dimensionValues", [])
            if isinstance(value, dict)
        ],
        "metrics": [
            str(value.get("value", ""))
            for value in row.get("metricValues", [])
            if isinstance(value, dict)
        ],
    }


def extract_error_payload(response: httpx.Response) -> dict[str, Any]:
    return {
        "status_code": response.status_code,
        "message": extract_error_message(response),
    }


def extract_error_message(response: httpx.Response) -> str:
    try:
        payload: dict[str, Any] = response.json()
    except ValueError:
        return response.text[:300]

    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("message", "unknown error"))[:300]
    if isinstance(error, str):
        return error[:300]
    return "unknown error"


if __name__ == "__main__":
    asyncio.run(main())
