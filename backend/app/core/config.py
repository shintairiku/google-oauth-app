from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Web App Standard API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    google_oauth_redirect_uri: str | None = None
    google_oauth_scopes: str = (
        "https://www.googleapis.com/auth/analytics.readonly "
        "https://www.googleapis.com/auth/webmasters.readonly"
    )
    google_oauth_system_name: str = "GA4 / Search Console OAuth連携"
    google_oauth_operation_name: str = "Google OAuth認証"
    google_oauth_connection_key: str = "internal_ga4_search_console"
    google_oauth_encrypted_refresh_token: str | None = None
    google_oauth_responsible_name: str = "認証システム責任者"
    google_oauth_contact: str = "管理者"
    token_encryption_key: str | None = None
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    oauth_state_ttl_seconds: int = 86400

    def require_google_oauth_client_id(self) -> str:
        return self._require("google_oauth_client_id")

    def require_google_oauth_client_secret(self) -> str:
        return self._require("google_oauth_client_secret")

    def require_google_oauth_redirect_uri(self) -> str:
        return self._require("google_oauth_redirect_uri")

    def require_google_oauth_encrypted_refresh_token(self) -> str:
        return self._require("google_oauth_encrypted_refresh_token")

    def require_token_encryption_key(self) -> str:
        return self._require("token_encryption_key")

    def require_supabase_url(self) -> str:
        return self._require("supabase_url").rstrip("/")

    def require_supabase_service_role_key(self) -> str:
        return self._require("supabase_service_role_key")

    def google_oauth_scope_list(self) -> list[str]:
        return [scope for scope in self.google_oauth_scopes.split() if scope]

    def _require(self, name: str) -> str:
        value = getattr(self, name)
        if value is None or value == "":
            raise ValueError(f"{name} is required")
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
