# Google OAuth App

GA4 / Search Console の読み取り権限を Google OAuth で取得し、`refresh_token` を暗号化して Supabase に保存するためのバックエンドです。

このリポジトリの初期目的は、OAuth 認証フローを完了して、継続取得に必要な `refresh_token` を安全に保存することです。保存済み token を使った GA4 / Search Console データ取得、接続解除 API、Google token revoke、管理画面は初期実装には含めていません。

## できること

- Google OAuth の認証開始 URL を発行する
- callback で `code` / `state` を受け取る
- `state` を検証する
- Google token endpoint で `code` を token に交換する
- `refresh_token` を暗号化する
- 暗号化済み `refresh_token` を Supabase に保存する
- 成功・失敗画面を backend から HTML で返す
- `.env` の暗号化済み token を使って、手動で Google API 疎通確認を行う

## 構成

```text
backend/
  app/
    api/routes/google_oauth.py          OAuth開始API / callback API / 完了画面
    services/google_oauth_service.py    OAuth処理の中心
    services/token_cipher.py            refresh tokenの暗号化・復号
    infrastructure/google_oauth_client.py
                                        Google OAuth URL生成 / token交換
    infrastructure/supabase_oauth_repository.py
                                        Supabaseへのstate/token保存
    core/config.py                      環境変数設定
  scripts/check_google_oauth_connection.py
                                        手動疎通確認スクリプト
  tests/                                backendテスト

supabase/
  migrations/                           OAuth保存用テーブル定義

docs/
  google-oauth-implementation-spec.md   実装仕様
  google-oauth-design.md                詳細設計
  google-oauth-ga4-search-console.md    背景説明
```

`frontend/` はテンプレート由来の最小 Next.js アプリです。現在の OAuth 完了画面は frontend ではなく backend が直接返します。

## 主なAPI

```text
GET /api/health
GET /api/oauth/google/start
GET /api/oauth/google/callback
```

`/api/oauth/google/start` にアクセスすると Google 同意画面へリダイレクトします。認証後、Google から `/api/oauth/google/callback` に戻り、token交換、暗号化、Supabase保存を行います。

## 保存先

Supabase に次のテーブルを作ります。

- `google_oauth_connections`
  - 暗号化済み `refresh_token`
  - 許可済み scope
  - access token の期限
  - 接続状態
- `google_oauth_states`
  - OAuth callback 検証用の `state_hash`
  - 有効期限
  - 消費済み日時

RLS は有効化し、`anon` / `authenticated` 向け policy は作りません。backend が `SUPABASE_SERVICE_ROLE_KEY` を使って保存します。

## 暗号化

`refresh_token` は保存前に Python の `cryptography` ライブラリの Fernet で暗号化します。

- 暗号化キーは `TOKEN_ENCRYPTION_KEY` で管理する
- 暗号化キーは Supabase に保存しない
- 平文 `refresh_token` はDB、レスポンス、ログに出さない
- 暗号化済み token を外部サーバへ返す API は作らない

`TOKEN_ENCRYPTION_KEY` と Supabase 上の `encrypted_refresh_token` が両方漏れると復号できるため、secret管理には注意してください。

## 環境変数

`backend/.env.example` を参考に設定します。

```env
APP_ENV=development

GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/oauth/google/callback
GOOGLE_OAUTH_SCOPES=https://www.googleapis.com/auth/analytics.readonly https://www.googleapis.com/auth/webmasters.readonly
GOOGLE_OAUTH_SYSTEM_NAME=GA4 / Search Console OAuth連携
GOOGLE_OAUTH_OPERATION_NAME=Google OAuth認証
GOOGLE_OAUTH_CONNECTION_KEY=internal_ga4_search_console
GOOGLE_OAUTH_RESPONSIBLE_NAME=認証システム責任者
GOOGLE_OAUTH_CONTACT=管理者

TOKEN_ENCRYPTION_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
OAUTH_STATE_TTL_SECONDS=86400
```

手動確認用に `GOOGLE_OAUTH_ENCRYPTED_REFRESH_TOKEN` もあります。確認後は `.env` から削除してください。

## ローカル起動

backend の依存関係を同期します。

```bash
cd backend
uv sync --extra dev
```

Supabase を起動し、migration を適用します。

```bash
npx supabase start
npx supabase db reset
```

backend を起動します。

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

ブラウザで OAuth を開始します。

```text
http://localhost:8000/api/oauth/google/start
```

失敗画面だけ確認したい場合は、次のURLを開きます。

```text
http://localhost:8000/api/oauth/google/callback?error=access_denied
```

## 手動疎通確認

Supabase に保存された `encrypted_refresh_token` を `backend/.env` の `GOOGLE_OAUTH_ENCRYPTED_REFRESH_TOKEN` に一時的に設定し、次を実行します。

```bash
cd backend
uv run python scripts/check_google_oauth_connection.py
```

このスクリプトは token 値を表示しません。access token の再発行、Search Console sites、GA4 Admin accounts の疎通だけ確認します。

## テスト

```bash
cd backend
uv run --extra dev ruff check .
uv run --extra dev pytest
```

現在のテストでは、state検証、token暗号化、レスポンスへのtoken非表示、本番での `/docs` 非公開などを確認しています。

## デプロイ時の注意

backend だけをデプロイすれば、現在のOAuthフローは動きます。frontend は必須ではありません。

本番環境では必ず次を設定してください。

```env
APP_ENV=production
GOOGLE_OAUTH_REDIRECT_URI=https://<backend-domain>/api/oauth/google/callback
```

`APP_ENV=production` の場合、FastAPI の自動ドキュメントは無効になります。

```text
/docs
/redoc
/openapi.json
```

Google Cloud Console には、本番の callback URL を redirect URI として登録してください。

```text
https://<backend-domain>/api/oauth/google/callback
```

## secret管理

次の値はGit、README、Slack、メール、ログに出さないでください。

- `GOOGLE_OAUTH_CLIENT_SECRET`
- `SUPABASE_SERVICE_ROLE_KEY`
- `TOKEN_ENCRYPTION_KEY`
- `GOOGLE_OAUTH_ENCRYPTED_REFRESH_TOKEN`

本番では `.env` ファイルではなく、Vercel などのホスティングサービスの Environment Variables / Secrets 機能に設定します。

## 仕様資料

詳細は `docs/` を参照してください。

- [実装仕様](docs/google-oauth-implementation-spec.md)
- [詳細設計](docs/google-oauth-design.md)
- [GA4 / Search Console OAuth説明](docs/google-oauth-ga4-search-console.md)
