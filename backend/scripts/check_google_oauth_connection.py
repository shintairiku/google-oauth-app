import asyncio
from typing import Any

import httpx

from app.core.config import settings
from app.services.token_cipher import TokenCipher


async def main() -> None:
    encrypted_refresh_token = settings.require_google_oauth_encrypted_refresh_token()
    refresh_token = TokenCipher(settings.require_token_encryption_key()).decrypt(
        encrypted_refresh_token
    )
    access_token = await refresh_access_token(refresh_token)

    print("OK: access token refreshed")
    await check_google_api(
        name="Search Console sites",
        url="https://www.googleapis.com/webmasters/v3/sites",
        access_token=access_token,
        count_key="siteEntry",
    )
    await check_google_api(
        name="GA4 Admin accounts",
        url="https://analyticsadmin.googleapis.com/v1beta/accounts",
        access_token=access_token,
        count_key="accounts",
    )


async def refresh_access_token(refresh_token: str) -> str:
    data = {
        "client_id": settings.require_google_oauth_client_id(),
        "client_secret": settings.require_google_oauth_client_secret(),
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post("https://oauth2.googleapis.com/token", data=data)
    if response.is_error:
        raise RuntimeError(f"access token refresh failed: {extract_error_message(response)}")

    access_token = response.json().get("access_token")
    if not access_token:
        raise RuntimeError("access_token was not returned")
    return access_token


async def check_google_api(name: str, url: str, access_token: str, count_key: str) -> None:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})

    if response.is_error:
        print(f"NG: {name}: {response.status_code} {extract_error_message(response)}")
        return

    items = response.json().get(count_key, [])
    count = len(items) if isinstance(items, list) else 0
    print(f"OK: {name}: {count} items")


def extract_error_message(response: httpx.Response) -> str:
    try:
        payload: dict[str, Any] = response.json()
    except ValueError:
        return response.text[:200]

    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("message", "unknown error"))[:200]
    if isinstance(error, str):
        return error[:200]
    return "unknown error"


if __name__ == "__main__":
    asyncio.run(main())
