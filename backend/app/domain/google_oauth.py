from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

ConnectionStatus = Literal["connected", "reauth_required", "error"]


@dataclass(frozen=True)
class GoogleTokenResponse:
    access_token: str
    expires_in: int
    refresh_token: str | None
    scope: str
    token_type: str


@dataclass(frozen=True)
class OAuthConnectionRecord:
    connection_key: str
    scopes: list[str]
    status: ConnectionStatus
    token_type: str | None = None
    access_token_expires_at: datetime | None = None
    encrypted_refresh_token: str | None = None
    google_account_email: str | None = None
    error_reason: str | None = None


@dataclass(frozen=True)
class OAuthCallbackResult:
    success: bool
    scopes: list[str] = field(default_factory=list)
    error_id: str | None = None
    error_reason: str | None = None
