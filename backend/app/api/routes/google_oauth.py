import html
import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.config import settings
from app.infrastructure.google_oauth_client import GoogleOAuthClient
from app.infrastructure.supabase_oauth_repository import SupabaseOAuthRepository
from app.services.google_oauth_service import GoogleOAuthService
from app.services.token_cipher import TokenCipher

router = APIRouter(prefix="/oauth/google", tags=["google-oauth"])
logger = logging.getLogger(__name__)

SCOPE_LABELS = {
    "https://www.googleapis.com/auth/analytics.readonly": (
        "Google Analytics の読み取り"
    ),
    "https://www.googleapis.com/auth/webmasters.readonly": (
        "Search Console の読み取り"
    ),
    "openid": "Googleアカウント識別情報の取得",
    "email": "Googleアカウントのメールアドレス取得",
}


def get_google_oauth_service() -> GoogleOAuthService:
    google_client = GoogleOAuthClient(
        client_id=settings.require_google_oauth_client_id(),
        client_secret=settings.require_google_oauth_client_secret(),
        redirect_uri=settings.require_google_oauth_redirect_uri(),
        scopes=settings.google_oauth_scope_list(),
    )
    repository = SupabaseOAuthRepository(
        supabase_url=settings.require_supabase_url(),
        service_role_key=settings.require_supabase_service_role_key(),
    )
    token_cipher = TokenCipher(settings.require_token_encryption_key())
    return GoogleOAuthService(
        google_client=google_client,
        repository=repository,
        token_cipher=token_cipher,
        connection_key=settings.google_oauth_connection_key,
        state_ttl_seconds=settings.oauth_state_ttl_seconds,
    )


@router.get("/start")
async def start_google_oauth(
    service: Annotated[GoogleOAuthService, Depends(get_google_oauth_service)],
) -> RedirectResponse:
    authorization_url = await service.create_authorization_redirect_url()
    return RedirectResponse(authorization_url)


@router.get("/callback", response_class=HTMLResponse)
async def handle_google_oauth_callback(
    service: Annotated[GoogleOAuthService, Depends(get_google_oauth_service)],
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    result = await service.handle_callback(code=code, state=state, error=error)
    if result.success:
        return HTMLResponse(render_success_html(result.scopes))

    error_id = result.error_id or "unknown"
    logger.warning(
        "Google OAuth callback failed",
        extra={"error_id": error_id, "error_reason": result.error_reason},
    )
    return HTMLResponse(render_failure_html(error_id), status_code=400)


def render_success_html(scopes: list[str]) -> str:
    system_name = html.escape(settings.google_oauth_system_name)
    operation_name = html.escape(settings.google_oauth_operation_name)
    responsible_name = html.escape(settings.google_oauth_responsible_name)
    contact = html.escape(settings.google_oauth_contact)
    connection_key = html.escape(settings.google_oauth_connection_key)
    scope_items = render_scope_items(scopes)
    return f"""
    <!doctype html>
    <html lang="ja">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Google連携が完了しました</title>
        <style>{base_styles()}</style>
      </head>
      <body>
        <main class="page">
          <section class="panel success">
            <div class="status">接続完了</div>
            <div class="system-name">{system_name}</div>
            <h1>Google連携が完了しました</h1>
            <p class="lead">
              {operation_name}が完了しました。この画面は閉じて問題ありません。
            </p>

            <div class="section">
              <h2>許可されたscope</h2>
              <ul>
                {scope_items}
              </ul>
            </div>

            <div class="section">
              <h2>連携を解除したい場合</h2>
              <p class="note">
                Googleアカウントの「サードパーティ製アプリとサービスへの接続」から、
                この連携のアクセス権を削除してください。
              </p>
            </div>

            <dl class="meta">
              <div><dt>接続キー</dt><dd>{connection_key}</dd></div>
              <div><dt>責任者</dt><dd>{responsible_name}</dd></div>
              <div><dt>問い合わせ先</dt><dd>{contact}</dd></div>
            </dl>
          </section>
        </main>
      </body>
    </html>
    """.strip()


def render_failure_html(error_id: str) -> str:
    system_name = html.escape(settings.google_oauth_system_name)
    operation_name = html.escape(settings.google_oauth_operation_name)
    responsible_name = html.escape(settings.google_oauth_responsible_name)
    contact = html.escape(settings.google_oauth_contact)
    escaped_error_id = html.escape(error_id)
    requested_scope_items = render_scope_items(settings.google_oauth_scope_list())
    return f"""
    <!doctype html>
    <html lang="ja">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Google連携に失敗しました</title>
        <style>{base_styles()}</style>
      </head>
      <body>
        <main class="page">
          <section class="panel failure">
            <div class="status">接続失敗</div>
            <div class="system-name">{system_name}</div>
            <h1>Google連携に失敗しました</h1>
            <p class="lead">
              {operation_name}を完了できませんでした。管理者へ下記のエラーIDを連絡してください。
            </p>

            <div class="section">
              <h2>要求していたscope</h2>
              <ul>
                {requested_scope_items}
              </ul>
            </div>

            <dl class="meta">
              <div><dt>システム名</dt><dd>{system_name}</dd></div>
              <div><dt>失敗した処理</dt><dd>{operation_name}</dd></div>
              <div><dt>エラーID</dt><dd>{escaped_error_id}</dd></div>
              <div><dt>責任者</dt><dd>{responsible_name}</dd></div>
              <div><dt>問い合わせ先</dt><dd>{contact}</dd></div>
            </dl>
          </section>
        </main>
      </body>
    </html>
    """.strip()


def render_scope_items(scopes: list[str]) -> str:
    if not scopes:
        return "<li>scope情報を取得できませんでした</li>"

    return "\n".join(render_scope_item(scope) for scope in scopes)


def render_scope_item(scope: str) -> str:
    label = SCOPE_LABELS.get(scope, scope)
    escaped_label = html.escape(label)
    escaped_scope = html.escape(scope)
    if label == scope:
        return f"<li><span>{escaped_scope}</span></li>"
    return f"<li><span>{escaped_label}</span><code>{escaped_scope}</code></li>"


def base_styles() -> str:
    return """
    :root {
      color-scheme: light;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #f5f7fb;
      color: #1f2937;
    }
    body {
      margin: 0;
      min-height: 100vh;
      background: #f5f7fb;
    }
    .page {
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 32px 16px;
      box-sizing: border-box;
    }
    .panel {
      width: min(720px, 100%);
      background: #ffffff;
      border: 1px solid #d8dee9;
      border-radius: 8px;
      padding: 32px;
      box-sizing: border-box;
      box-shadow: 0 16px 40px rgba(31, 41, 55, 0.08);
    }
    .panel.success { border-top: 6px solid #2563eb; }
    .panel.failure { border-top: 6px solid #dc2626; }
    .status {
      display: inline-block;
      margin-bottom: 16px;
      padding: 4px 10px;
      border-radius: 999px;
      background: #e8f0fe;
      color: #1d4ed8;
      font-size: 13px;
      font-weight: 700;
    }
    .system-name {
      margin-bottom: 8px;
      color: #4b5563;
      font-size: 15px;
      font-weight: 700;
    }
    .failure .status {
      background: #fee2e2;
      color: #b91c1c;
    }
    h1 {
      margin: 0 0 12px;
      font-size: 28px;
      line-height: 1.25;
      letter-spacing: 0;
    }
    .lead {
      margin: 0 0 24px;
      color: #4b5563;
      line-height: 1.75;
    }
    .note {
      margin: 0;
      color: #374151;
      line-height: 1.75;
    }
    .section {
      border-top: 1px solid #e5e7eb;
      padding-top: 20px;
      margin-top: 20px;
    }
    h2 {
      margin: 0 0 10px;
      font-size: 16px;
      letter-spacing: 0;
    }
    ul {
      margin: 0;
      padding-left: 20px;
      color: #374151;
      line-height: 1.8;
    }
    li code {
      display: block;
      margin-top: 2px;
      color: #6b7280;
      font-size: 13px;
      overflow-wrap: anywhere;
    }
    .meta {
      margin: 24px 0 0;
      border-top: 1px solid #e5e7eb;
    }
    .meta div {
      display: grid;
      grid-template-columns: 140px 1fr;
      gap: 16px;
      padding: 14px 0;
      border-bottom: 1px solid #e5e7eb;
    }
    dt {
      color: #6b7280;
      font-weight: 700;
    }
    dd {
      margin: 0;
      color: #111827;
      overflow-wrap: anywhere;
    }
    @media (max-width: 560px) {
      .panel { padding: 24px; }
      .meta div { grid-template-columns: 1fr; gap: 4px; }
      h1 { font-size: 24px; }
    }
    """
