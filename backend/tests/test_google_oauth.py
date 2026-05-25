import asyncio
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.api.routes.google_oauth import get_google_oauth_service
from app.domain.google_oauth import GoogleTokenResponse, OAuthCallbackResult, OAuthConnectionRecord
from app.infrastructure.google_oauth_client import GoogleOAuthClient
from app.main import app
from app.services.google_oauth_service import GoogleOAuthService, hash_state
from app.services.token_cipher import TokenCipher


class FakeRepository:
    def __init__(self) -> None:
        self.states: dict[str, tuple[str, datetime, bool]] = {}
        self.connections: list[OAuthConnectionRecord] = []

    async def save_state(self, state_hash: str, connection_key: str, expires_at: datetime) -> None:
        self.states[state_hash] = (connection_key, expires_at, False)

    async def consume_state(self, state_hash: str, now: datetime) -> str | None:
        state = self.states.get(state_hash)
        if state is None:
            return None
        connection_key, expires_at, consumed = state
        if consumed or expires_at <= now:
            return None
        self.states[state_hash] = (connection_key, expires_at, True)
        return connection_key

    async def upsert_connection(self, connection: OAuthConnectionRecord) -> None:
        self.connections.append(connection)


class FakeGoogleClient:
    def __init__(self, token_response: GoogleTokenResponse | None = None) -> None:
        self.token_response = token_response or GoogleTokenResponse(
            access_token="access-token",
            expires_in=3600,
            refresh_token="refresh-token",
            scope="scope-a scope-b",
            token_type="Bearer",
        )
        self.exchanged_codes: list[str] = []

    def build_authorization_url(self, state: str) -> str:
        return f"https://accounts.google.com/o/oauth2/v2/auth?state={state}"

    async def exchange_code(self, code: str) -> GoogleTokenResponse:
        self.exchanged_codes.append(code)
        return self.token_response


class FakeRouteService:
    def __init__(self, result: OAuthCallbackResult | None = None) -> None:
        self.result = result or OAuthCallbackResult(
            success=True,
            scopes=[
                "https://www.googleapis.com/auth/analytics.readonly",
                "https://www.googleapis.com/auth/webmasters.readonly",
                "https://example.com/auth/custom.readonly",
            ],
        )

    async def create_authorization_redirect_url(self) -> str:
        return "https://accounts.google.com/o/oauth2/v2/auth?state=test-state"

    async def handle_callback(
        self,
        code: str | None,
        state: str | None,
        error: str | None,
    ) -> OAuthCallbackResult:
        return self.result


def test_token_cipher_encrypts_and_decrypts() -> None:
    cipher = TokenCipher(Fernet.generate_key().decode("utf-8"))

    encrypted = cipher.encrypt("refresh-token")

    assert encrypted != "refresh-token"
    assert cipher.decrypt(encrypted) == "refresh-token"


def test_google_authorization_url_contains_required_parameters() -> None:
    client = GoogleOAuthClient(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="https://example.com/api/oauth/google/callback",
        scopes=["scope-a", "scope-b"],
    )

    authorization_url = client.build_authorization_url("state-value")
    parsed = urlparse(authorization_url)
    query = parse_qs(parsed.query)

    assert parsed.netloc == "accounts.google.com"
    assert query["client_id"] == ["client-id"]
    assert query["redirect_uri"] == ["https://example.com/api/oauth/google/callback"]
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["scope-a scope-b"]
    assert query["access_type"] == ["offline"]
    assert query["prompt"] == ["consent"]
    assert query["state"] == ["state-value"]


def test_create_authorization_redirect_url_saves_hashed_state() -> None:
    repository = FakeRepository()
    service = GoogleOAuthService(
        google_client=FakeGoogleClient(),
        repository=repository,
        token_cipher=TokenCipher(Fernet.generate_key().decode("utf-8")),
        connection_key="internal_ga4_search_console",
        state_ttl_seconds=86400,
    )

    result = asyncio.run(service.create_authorization_redirect_url())
    state = parse_qs(urlparse(result).query)["state"][0]

    assert state not in repository.states
    assert hash_state(state) in repository.states


def test_callback_rejects_invalid_state_without_token_exchange() -> None:
    google_client = FakeGoogleClient()
    service = GoogleOAuthService(
        google_client=google_client,
        repository=FakeRepository(),
        token_cipher=TokenCipher(Fernet.generate_key().decode("utf-8")),
        connection_key="internal_ga4_search_console",
        state_ttl_seconds=86400,
    )

    result = asyncio.run(service.handle_callback("code", "invalid-state", None))

    assert result.success is False
    assert result.error_reason == "invalid_state"
    assert google_client.exchanged_codes == []


def test_callback_saves_only_encrypted_refresh_token() -> None:
    repository = FakeRepository()
    google_client = FakeGoogleClient()
    cipher = TokenCipher(Fernet.generate_key().decode("utf-8"))
    service = GoogleOAuthService(
        google_client=google_client,
        repository=repository,
        token_cipher=cipher,
        connection_key="internal_ga4_search_console",
        state_ttl_seconds=86400,
    )
    state = "valid-state"
    now = datetime.now(UTC)
    repository.states[hash_state(state)] = (
        "internal_ga4_search_console",
        now + timedelta(days=1),
        False,
    )

    result = asyncio.run(service.handle_callback("code", state, None))

    assert result.success is True
    assert result.scopes == ["scope-a", "scope-b"]
    assert repository.connections[-1].status == "connected"
    encrypted_refresh_token = repository.connections[-1].encrypted_refresh_token
    assert encrypted_refresh_token is not None
    assert encrypted_refresh_token != "refresh-token"
    assert cipher.decrypt(encrypted_refresh_token) == "refresh-token"


def test_callback_without_refresh_token_saves_reauth_required() -> None:
    repository = FakeRepository()
    google_client = FakeGoogleClient(
        GoogleTokenResponse(
            access_token="access-token",
            expires_in=3600,
            refresh_token=None,
            scope="scope-a",
            token_type="Bearer",
        )
    )
    service = GoogleOAuthService(
        google_client=google_client,
        repository=repository,
        token_cipher=TokenCipher(Fernet.generate_key().decode("utf-8")),
        connection_key="internal_ga4_search_console",
        state_ttl_seconds=86400,
    )
    state = "valid-state"
    repository.states[hash_state(state)] = (
        "internal_ga4_search_console",
        datetime.now(UTC) + timedelta(days=1),
        False,
    )

    result = asyncio.run(service.handle_callback("code", state, None))

    assert result.success is False
    assert result.error_reason == "refresh_token_missing"
    assert repository.connections[-1].status == "reauth_required"
    assert repository.connections[-1].encrypted_refresh_token is None


def test_start_route_redirects_to_google() -> None:
    app.dependency_overrides[get_google_oauth_service] = lambda: FakeRouteService()
    client = TestClient(app)

    response = client.get("/api/oauth/google/start", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"].startswith("https://accounts.google.com/")
    app.dependency_overrides.clear()


def test_callback_success_response_shows_authorized_access_without_tokens() -> None:
    app.dependency_overrides[get_google_oauth_service] = lambda: FakeRouteService()
    client = TestClient(app)

    response = client.get("/api/oauth/google/callback?code=code&state=state")

    assert response.status_code == 200
    assert "Google連携が完了しました" in response.text
    assert "許可されたscope" in response.text
    assert "Google Analytics の読み取り" in response.text
    assert "Search Console の読み取り" in response.text
    assert "https://example.com/auth/custom.readonly" in response.text
    assert "接続キー" in response.text
    assert "責任者" in response.text
    assert "問い合わせ先" in response.text
    assert "refresh-token" not in response.text
    assert "access-token" not in response.text
    assert "encrypted" not in response.text
    app.dependency_overrides.clear()


def test_callback_failure_response_includes_error_id_and_contact_only() -> None:
    app.dependency_overrides[get_google_oauth_service] = lambda: FakeRouteService(
        OAuthCallbackResult(success=False, error_id="error-id", error_reason="invalid_state")
    )
    client = TestClient(app)

    response = client.get("/api/oauth/google/callback?error=access_denied")

    assert response.status_code == 400
    assert "Google連携に失敗しました" in response.text
    assert "完了できませんでした" in response.text
    assert "要求していたscope" in response.text
    assert "https://www.googleapis.com/auth/analytics.readonly" in response.text
    assert "https://www.googleapis.com/auth/webmasters.readonly" in response.text
    assert "システム名" in response.text
    assert "失敗した処理" in response.text
    assert "エラーID" in response.text
    assert "error-id" in response.text
    assert "責任者" in response.text
    assert "問い合わせ先" in response.text
    assert "invalid_state" not in response.text
    assert "refresh-token" not in response.text
    assert "access-token" not in response.text
    app.dependency_overrides.clear()
