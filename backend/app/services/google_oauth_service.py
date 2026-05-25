import secrets
import uuid
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from app.domain.google_oauth import OAuthCallbackResult, OAuthConnectionRecord
from app.infrastructure.google_oauth_client import GoogleOAuthClient
from app.infrastructure.supabase_oauth_repository import SupabaseOAuthRepository
from app.services.token_cipher import TokenCipher


class GoogleOAuthService:
    def __init__(
        self,
        google_client: GoogleOAuthClient,
        repository: SupabaseOAuthRepository,
        token_cipher: TokenCipher,
        connection_key: str,
        state_ttl_seconds: int,
    ) -> None:
        self._google_client = google_client
        self._repository = repository
        self._token_cipher = token_cipher
        self._connection_key = connection_key
        self._state_ttl_seconds = state_ttl_seconds

    async def create_authorization_redirect_url(self) -> str:
        state = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        await self._repository.save_state(
            state_hash=hash_state(state),
            connection_key=self._connection_key,
            expires_at=now + timedelta(seconds=self._state_ttl_seconds),
        )
        return self._google_client.build_authorization_url(state)

    async def handle_callback(
        self,
        code: str | None,
        state: str | None,
        error: str | None,
    ) -> OAuthCallbackResult:
        if error:
            return failure("oauth_denied")
        if not code:
            return failure("missing_code")
        if not state:
            return failure("missing_state")

        now = datetime.now(UTC)
        connection_key = await self._repository.consume_state(hash_state(state), now)
        if connection_key is None:
            return failure("invalid_state")

        try:
            token = await self._google_client.exchange_code(code)
        except Exception:
            return failure("token_exchange_failed")

        scopes = [scope for scope in token.scope.split() if scope]
        access_token_expires_at = now + timedelta(seconds=token.expires_in)
        google_account_email = await self._fetch_google_account_email(token.access_token)

        if not token.refresh_token:
            try:
                await self._repository.upsert_connection(
                    OAuthConnectionRecord(
                        connection_key=connection_key,
                        scopes=scopes,
                        status="reauth_required",
                        token_type=token.token_type,
                        access_token_expires_at=access_token_expires_at,
                        google_account_email=google_account_email,
                        error_reason="refresh_token_missing",
                    )
                )
            except Exception:
                return failure("supabase_save_failed")
            return failure("refresh_token_missing")

        try:
            encrypted_refresh_token = self._token_cipher.encrypt(token.refresh_token)
        except Exception:
            return failure("token_encrypt_failed")

        try:
            await self._repository.upsert_connection(
                OAuthConnectionRecord(
                    connection_key=connection_key,
                    scopes=scopes,
                    status="connected",
                    token_type=token.token_type,
                    access_token_expires_at=access_token_expires_at,
                    encrypted_refresh_token=encrypted_refresh_token,
                    google_account_email=google_account_email,
                )
            )
        except Exception:
            return failure("supabase_save_failed")

        return OAuthCallbackResult(success=True, scopes=scopes)

    async def _fetch_google_account_email(self, access_token: str) -> str | None:
        try:
            userinfo = await self._google_client.fetch_userinfo(access_token)
        except Exception:
            return None
        return userinfo.email


def hash_state(state: str) -> str:
    return sha256(state.encode("utf-8")).hexdigest()


def failure(reason: str) -> OAuthCallbackResult:
    return OAuthCallbackResult(success=False, error_id=uuid.uuid4().hex, error_reason=reason)
