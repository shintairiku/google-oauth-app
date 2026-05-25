# GA4 / Search Console OAuth連携 詳細設計

## 目的

`docs/google-oauth-implementation-spec.md` の実装仕様を、FastAPI backendへ実装できる単位に分解する。

初期実装の責務は、Google OAuthで `refresh_token` を取得し、Fernetで暗号化してSupabaseへ保存するところまでとする。

## 設計方針

- API層はHTTP入出力、リダイレクト、HTMLレスポンスだけを担当する
- OAuthの業務手順はサービス層に置く
- 暗号化、Google token endpoint、Supabase操作はインフラ層に分離する
- `refresh_token`、`access_token`、`code`、client secret、暗号化キーはログやレスポンスに出さない
- `.env` による手動確認は自動テストと分離する

## 追加する依存関係

`backend/pyproject.toml` に追加する。

```toml
dependencies = [
  "cryptography>=42.0.0,<46.0.0",
  "httpx>=0.27.0,<1.0.0",
]
```

`httpx` はGoogle token endpointとSupabase REST APIの呼び出しに使う。dev依存にも既にあるが、実行時にも必要なため通常依存へ移す。

## 環境変数設計

`backend/app/core/config.py` に追加する。

| 変数名 | 型 | 必須 | 用途 |
| --- | --- | --- | --- |
| `GOOGLE_OAUTH_CLIENT_ID` | `str` | 必須 | Google OAuth client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | `str` | 必須 | Google OAuth client secret |
| `GOOGLE_OAUTH_REDIRECT_URI` | `str` | 必須 | callback URL |
| `GOOGLE_OAUTH_SCOPES` | `str` | 任意 | scopeの空白区切り文字列 |
| `GOOGLE_OAUTH_SYSTEM_NAME` | `str` | 任意 | callback画面に表示するシステム名 |
| `GOOGLE_OAUTH_OPERATION_NAME` | `str` | 任意 | callback失敗画面に表示する処理名 |
| `GOOGLE_OAUTH_CONNECTION_KEY` | `str` | 任意 | 接続用途キー |
| `TOKEN_ENCRYPTION_KEY` | `str` | 必須 | Fernet暗号化キー |
| `SUPABASE_URL` | `str` | 必須 | Supabase URL |
| `SUPABASE_SERVICE_ROLE_KEY` | `str` | 必須 | Supabase service role key |
| `OAUTH_STATE_TTL_SECONDS` | `int` | 任意 | state有効期限 |
| `GOOGLE_OAUTH_RESPONSIBLE_NAME` | `str` | 任意 | callback画面に表示する責任者名 |
| `GOOGLE_OAUTH_CONTACT` | `str` | 任意 | callback画面に表示する問い合わせ先 |

デフォルト値:

```text
GOOGLE_OAUTH_SCOPES="https://www.googleapis.com/auth/analytics.readonly https://www.googleapis.com/auth/webmasters.readonly openid email"
GOOGLE_OAUTH_SYSTEM_NAME="GA4 / Search Console OAuth連携"
GOOGLE_OAUTH_OPERATION_NAME="Google OAuth認証"
GOOGLE_OAUTH_CONNECTION_KEY="internal_ga4_search_console"
OAUTH_STATE_TTL_SECONDS=86400
```

必須値が未設定の場合、OAuth関連API実行時に設定エラーとして失敗させる。

## ディレクトリ設計

```text
backend/app/
  api/routes/google_oauth.py
  domain/google_oauth.py
  services/google_oauth_service.py
  services/token_cipher.py
  infrastructure/google_oauth_client.py
  infrastructure/supabase_oauth_repository.py
  schemas/google_oauth.py
```

## 各ファイルの責務

### `api/routes/google_oauth.py`

FastAPI routeを定義する。

- `GET /api/oauth/google/start`
- `GET /api/oauth/google/callback`

`start` はGoogle認証URLへ `RedirectResponse` する。

`callback` は成功時・失敗時ともHTMLを返す。失敗時にはエラーIDを表示する。

API層ではtoken値を扱わない。処理は `GoogleOAuthService` に委譲する。

### `domain/google_oauth.py`

OAuth連携で使う値と状態を定義する。

想定する型:

```python
ConnectionStatus = Literal["connected", "reauth_required", "error"]

@dataclass(frozen=True)
class OAuthState:
    state: str
    state_hash: str
    connection_key: str
    expires_at: datetime

@dataclass(frozen=True)
class GoogleTokenResponse:
    access_token: str
    expires_in: int
    refresh_token: str | None
    scope: str
    token_type: str

@dataclass(frozen=True)
class GoogleUserInfo:
    email: str | None
```

### `services/token_cipher.py`

Fernetによる暗号化・復号を担当する。

公開メソッド:

```python
class TokenCipher:
    def encrypt(self, plain_text: str) -> str: ...
    def decrypt(self, encrypted_text: str) -> str: ...
```

初期実装では保存時の暗号化に使う。復号はテストと将来拡張のために用意するが、業務機能からは呼ばない。

### `infrastructure/google_oauth_client.py`

Google OAuthへの外部HTTP通信を担当する。

公開メソッド:

```python
class GoogleOAuthClient:
    def build_authorization_url(self, state: str) -> str: ...
    async def exchange_code(self, code: str) -> GoogleTokenResponse: ...
```

`build_authorization_url` は次のパラメータを含むURLを生成する。

- `client_id`
- `redirect_uri`
- `response_type=code`
- `scope`
- `access_type=offline`
- `prompt=consent`
- `state`

`exchange_code` は `POST https://oauth2.googleapis.com/token` を呼び出す。

`fetch_userinfo` は `GET https://openidconnect.googleapis.com/v1/userinfo` を呼び出し、認証したGoogleアカウントのメールアドレスを取得する。メールアドレスは運用確認用の情報であり、暗号化せず `google_account_email` に保存する。

### `infrastructure/supabase_oauth_repository.py`

Supabase REST APIでstateとconnectionを操作する。

公開メソッド:

```python
class SupabaseOAuthRepository:
    async def save_state(self, state_hash: str, connection_key: str, expires_at: datetime) -> None: ...
    async def consume_state(self, state_hash: str, now: datetime) -> str | None: ...
    async def upsert_connection(self, connection: OAuthConnectionRecord) -> None: ...
```

`consume_state` は、未使用かつ期限内のstateだけを有効とし、成功時に `consumed_at` を更新して `connection_key` を返す。

`upsert_connection` は `connection_key` と `google_account_email` のunique制約に基づいて、既存行があれば更新、なければ作成する。これにより、同じ用途のOAuth連携でも複数のGoogleアカウントを別々の接続として保存できる。

### `services/google_oauth_service.py`

OAuth処理の中心。

公開メソッド:

```python
class GoogleOAuthService:
    async def create_authorization_redirect_url(self) -> str: ...
    async def handle_callback(self, code: str | None, state: str | None, error: str | None) -> OAuthCallbackResult: ...
```

`create_authorization_redirect_url` の流れ:

1. ランダムな `state` を生成する
2. `state_hash` を生成する
3. `google_oauth_states` に保存する
4. Google認証URLを返す

`handle_callback` の流れ:

1. `error` があれば失敗結果を返す
2. `code` / `state` がなければ失敗結果を返す
3. `state_hash` を生成し、Supabaseで検証・消費する
4. Google token endpointで `code` をtokenへ交換する
5. Google UserInfo endpointでメールアドレスを取得する
6. `refresh_token` がなければ `reauth_required` として保存する
7. `refresh_token` があれば暗号化する
8. `google_oauth_connections` にupsertする
9. 成功結果を返す

### `schemas/google_oauth.py`

APIレスポンスのJSON schemaは初期実装では使わない。将来の管理API用に空で作成するか、必要になるまで作成しない。

## Supabase migration設計

`supabase/migrations/` に新しいmigrationを追加する。

```sql
create table if not exists google_oauth_connections (
  id uuid primary key default gen_random_uuid(),
  connection_key text not null,
  google_account_email text,
  scopes text[] not null,
  token_type text,
  access_token_expires_at timestamptz,
  encrypted_refresh_token text,
  status text not null,
  error_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint google_oauth_connections_status_check
    check (status in ('connected', 'reauth_required', 'error'))
);

create unique index if not exists google_oauth_connections_connection_key_google_account_email_key
  on google_oauth_connections (connection_key, google_account_email);

create table if not exists google_oauth_states (
  id uuid primary key default gen_random_uuid(),
  state_hash text not null,
  connection_key text not null,
  expires_at timestamptz not null,
  consumed_at timestamptz,
  created_at timestamptz not null default now()
);

create unique index if not exists google_oauth_states_state_hash_key
  on google_oauth_states (state_hash);

alter table google_oauth_connections enable row level security;
alter table google_oauth_states enable row level security;
```

`anon` / `authenticated` 向けpolicyは作らない。

## state生成・hash設計

`state` は `secrets.token_urlsafe(32)` で生成する。

`state_hash` はSHA-256で作る。

```text
state_hash = sha256(state.encode("utf-8")).hexdigest()
```

平文 `state` はSupabaseに保存しない。

## HTMLレスポンス設計

成功時:

```html
<h1>Google連携が完了しました</h1>
<p>GA4 / Search Console OAuth連携</p>
<p>Google OAuth認証が完了しました。</p>
<h2>許可されたscope</h2>
<ul>
  <li>Google token responseで返されたscope</li>
</ul>
<h2>連携を解除したい場合</h2>
<p>Googleアカウントの「サードパーティ製アプリとサービスへの接続」から、この連携のアクセス権を削除してください。</p>
<dl>接続キー、責任者、問い合わせ先</dl>
```

失敗時:

```html
<h1>Google連携に失敗しました</h1>
<p>GA4 / Search Console OAuth連携</p>
<p>Google OAuth認証を完了できませんでした。</p>
<p>管理者へ下記のエラーIDを連絡してください。</p>
<h2>要求していたscope</h2>
<ul>
  <li>GOOGLE_OAUTH_SCOPESで要求したscope</li>
</ul>
<dl>システム名、失敗した処理、エラーID、責任者、問い合わせ先</dl>
```

`error_id` は `uuid.uuid4().hex` で生成する。ログには `error_id` とエラー種別を残す。token、code、secretはログに含めない。

成功時のscope表示はGoogle token responseの `scope` を使う。失敗時はtoken responseを取得できない場合があるため、`GOOGLE_OAUTH_SCOPES` で要求していたscopeを表示する。既知scopeは日本語ラベルとscope URLを併記し、未知scopeはscope URLをそのまま表示する。

## エラー種別

内部的なエラー種別:

```text
oauth_denied
missing_code
missing_state
invalid_state
expired_state
token_exchange_failed
refresh_token_missing
token_encrypt_failed
supabase_save_failed
settings_missing
unexpected_error
```

ユーザー表示はすべて同じ失敗HTMLに寄せる。

## テスト設計

### unit test

- `TokenCipher` が暗号化・復号できる
- `TokenCipher` の暗号文が平文と一致しない
- `state_hash` が決定的に生成される
- Google認証URLに必要パラメータが含まれる
- callbackで `error` がある場合、token交換しない
- callbackで `state` が不正な場合、token交換しない
- `refresh_token` がない場合、`reauth_required` として保存する
- `refresh_token` がある場合、暗号化済み値だけ保存する
- UserInfo endpointから取得したメールアドレスを保存する

### API test

- `GET /api/oauth/google/start` がGoogle認証URLへリダイレクトする
- `GET /api/oauth/google/callback?error=...` がシステム名、失敗した処理、要求していたscope、連絡先を含む失敗HTMLを返す
- 成功callbackが実際に許可されたscopeと責任者情報を含む成功HTMLを返す
- 成功callbackがGoogleアカウント側で連携解除できる旨を返す
- レスポンスに `access_token`、`refresh_token`、暗号化済みtoken、client secretが含まれない

### 手動確認

`.env` に実Google OAuth設定を入れて、ブラウザで `/api/oauth/google/start` にアクセスする。

確認すること:

- Google同意画面へ遷移する
- callback後に成功HTMLが表示される
- Supabaseの `google_oauth_connections` に暗号化済みtokenが保存される
- 平文tokenがDB、レスポンス、ログに出ない

保存後、Supabase Studioで `google_oauth_connections.encrypted_refresh_token` をコピーし、`.env` に設定する。

```env
GOOGLE_OAUTH_ENCRYPTED_REFRESH_TOKEN=コピーした暗号化済みtoken
```

次のコマンドで、`.env` の暗号化済みrefresh tokenを復号し、access tokenを再発行してGoogle APIの疎通確認を行う。

```bash
cd backend
uv run python scripts/check_google_oauth_connection.py
```

このスクリプトはtoken値を表示しない。確認対象はSearch Consoleのサイト一覧とGA4 Adminのアカウント一覧とする。

## 実装順序

1. Supabase migrationを追加する
2. `Settings` にOAuth / Supabase / 暗号化設定を追加する
3. `TokenCipher` とテストを追加する
4. Google認証URL生成を実装する
5. Supabase state repositoryを実装する
6. OAuth開始APIを実装する
7. Google token交換clientを実装する
8. Supabase connection repositoryを実装する
9. callback処理を実装する
10. APIテストを追加する
11. `.env.example` と手動確認手順を更新する

## コミット分割案

1. `docs: OAuth連携の詳細設計を追加`
2. `chore: OAuth連携用の依存関係と設定を追加`
3. `feat: OAuth連携用のSupabase schemaを追加`
4. `feat: OAuth開始APIを追加`
5. `feat: OAuth callbackでrefresh tokenを暗号化保存`
6. `test: OAuth連携のテストを追加`
