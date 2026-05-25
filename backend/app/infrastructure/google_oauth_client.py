from urllib.parse import urlencode

import httpx

from app.domain.google_oauth import GoogleTokenResponse, GoogleUserInfo


class GoogleOAuthClient:
    authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
    token_endpoint = "https://oauth2.googleapis.com/token"
    userinfo_endpoint = "https://openidconnect.googleapis.com/v1/userinfo"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: list[str],
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._scopes = scopes

    def build_authorization_url(self, state: str) -> str:
        query = urlencode(
            {
                "client_id": self._client_id,
                "redirect_uri": self._redirect_uri,
                "response_type": "code",
                "scope": " ".join(self._scopes),
                "access_type": "offline",
                "prompt": "consent",
                "state": state,
            }
        )
        return f"{self.authorization_endpoint}?{query}"

    async def exchange_code(self, code: str) -> GoogleTokenResponse:
        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "redirect_uri": self._redirect_uri,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(self.token_endpoint, data=data)
            response.raise_for_status()

        payload = response.json()
        return GoogleTokenResponse(
            access_token=payload["access_token"],
            expires_in=int(payload.get("expires_in", 0)),
            refresh_token=payload.get("refresh_token"),
            scope=payload.get("scope", ""),
            token_type=payload.get("token_type", "Bearer"),
        )

    async def fetch_userinfo(self, access_token: str) -> GoogleUserInfo:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                self.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()

        payload = response.json()
        email = payload.get("email")
        return GoogleUserInfo(email=email if isinstance(email, str) else None)
