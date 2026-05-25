from datetime import UTC, datetime
from typing import Any

import httpx

from app.domain.google_oauth import OAuthConnectionRecord


class SupabaseOAuthRepository:
    def __init__(self, supabase_url: str, service_role_key: str) -> None:
        self._rest_url = f"{supabase_url.rstrip('/')}/rest/v1"
        self._headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
        }

    async def save_state(self, state_hash: str, connection_key: str, expires_at: datetime) -> None:
        payload = {
            "state_hash": state_hash,
            "connection_key": connection_key,
            "expires_at": _format_datetime(expires_at),
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self._rest_url}/google_oauth_states",
                headers={**self._headers, "Prefer": "return=minimal"},
                json=payload,
            )
            response.raise_for_status()

    async def consume_state(self, state_hash: str, now: datetime) -> str | None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            select_response = await client.get(
                f"{self._rest_url}/google_oauth_states",
                headers=self._headers,
                params={
                    "state_hash": f"eq.{state_hash}",
                    "consumed_at": "is.null",
                    "expires_at": f"gt.{_format_datetime(now)}",
                    "select": "id,connection_key",
                    "limit": "1",
                },
            )
            select_response.raise_for_status()
            rows: list[dict[str, Any]] = select_response.json()
            if not rows:
                return None

            state_id = rows[0]["id"]
            connection_key = rows[0]["connection_key"]
            update_response = await client.patch(
                f"{self._rest_url}/google_oauth_states",
                headers={**self._headers, "Prefer": "return=minimal"},
                params={
                    "id": f"eq.{state_id}",
                    "consumed_at": "is.null",
                },
                json={"consumed_at": _format_datetime(now)},
            )
            update_response.raise_for_status()
            return connection_key

    async def upsert_connection(self, connection: OAuthConnectionRecord) -> None:
        payload = {
            "connection_key": connection.connection_key,
            "google_account_email": connection.google_account_email,
            "scopes": connection.scopes,
            "token_type": connection.token_type,
            "access_token_expires_at": (
                _format_datetime(connection.access_token_expires_at)
                if connection.access_token_expires_at
                else None
            ),
            "encrypted_refresh_token": connection.encrypted_refresh_token,
            "status": connection.status,
            "error_reason": connection.error_reason,
            "updated_at": _format_datetime(datetime.now(UTC)),
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self._rest_url}/google_oauth_connections",
                headers={
                    **self._headers,
                    "Prefer": "resolution=merge-duplicates,return=minimal",
                },
                params={"on_conflict": "connection_key"},
                json=payload,
            )
            response.raise_for_status()


def _format_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
