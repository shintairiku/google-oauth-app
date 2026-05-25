# GA4 / Search Console OAuth連携 実装仕様書

詳細設計は [GA4 / Search Console OAuth連携 詳細設計](./google-oauth-design.md) を参照します。

## 目的

Google OAuthを使ってGA4 / Search Consoleの読み取り権限を取得し、バックエンドで `refresh_token` を安全に保存する。

この仕様書では、初期実装で作る範囲、作らない範囲、API、保存方針、暗号化方針、セキュリティ要件、テスト観点を定義する。

このサーバの初期目的は、Google OAuthで `refresh_token` を確保し、暗号化して保存することに限定する。保存したtokenを使ったGA4 / Search Console API呼び出しは初期実装では行わない。

## 初期実装の対象範囲

初期実装では、Google OAuthの認可開始から `refresh_token` の暗号化保存までを対象にする。

- Google認証URLを発行する
- `state` を生成し、callback時に検証する
- Googleから `code` を受け取る
- `code` をGoogle token endpointへ送信し、tokenに交換する
- `refresh_token` を取得する
- `refresh_token` をバックエンドで暗号化する
- 暗号化済み `refresh_token` をSupabaseに保存する
- 認証したGoogleアカウントのメールアドレスを取得して保存する
- 接続状態、scope、期限情報を保存する
- 失敗時に再認証や設定不備を判別できる状態にする

初期実装では、GA4 / Search Console APIを呼ぶ処理は作らない。接続確認としてのプロパティ一覧取得も初期実装には含めない。

## 初期実装で作らないもの

- GA4レポートデータの定期取得
- Search Console検索パフォーマンスの定期取得
- 複数プロパティの取得ジョブ管理
- 管理画面の詳細な接続一覧
- KMSによる鍵管理
- refresh tokenの自動ローテーション
- 暗号化済みtokenを外部サーバへ返すAPI
- 保存済みtokenを使ったGoogle API呼び出し
- 接続解除API
- Google token revoke
- GA4 / Search Consoleプロパティ一覧取得

## 全体構成

```text
利用者
  ↓
FrontendまたはBackend URL
  ↓
Backend: OAuth開始API
  ↓ state生成・保存、Google認証URLへリダイレクト
Google同意画面
  ↓ code/state付きでcallback
Backend: OAuth callback API
  ↓ state検証、codeをtokenへ交換
Backend: Token暗号化
  ↓
Supabase: 暗号化済みrefresh token保存
```

フロントエンドは必須ではない。フロントエンドを使う場合でも、役割はGoogle連携の開始操作に限定する。

`client_secret`、`state` 管理、token交換、暗号化、Supabase保存はバックエンドで行う。

暗号化済みtoken、平文token、暗号化キーは他サーバへ渡さない。将来、保存済みtokenを使ってGoogle APIを呼ぶ機能を作る場合も、このバックエンド側で復号して利用する方針とする。

## API仕様

### OAuth開始API

```text
GET /api/oauth/google/start
```

Google OAuthの認証URLを生成し、Google同意画面へリダイレクトする。

処理内容:

- 接続用途を識別する `connection_key` を決定する
- ランダムな `state` を生成する
- `state` と `connection_key` を一時保存する
- Google OAuth認証URLを生成する
- Google同意画面へリダイレクトする

認証URLに含める主なパラメータ:

| パラメータ | 値 |
| --- | --- |
| `client_id` | 環境変数のGoogle OAuth client ID |
| `redirect_uri` | 環境変数のcallback URL |
| `response_type` | `code` |
| `scope` | GA4 / Search Consoleの読み取り専用scope |
| `access_type` | `offline` |
| `prompt` | 初期実装では `consent` を指定する |
| `state` | バックエンドで生成したランダム値 |

初期scope:

```text
https://www.googleapis.com/auth/analytics.readonly
https://www.googleapis.com/auth/webmasters.readonly
openid
email
```

社内アプリとしての初期実装では、`connection_key` は固定値 `internal_ga4_search_console` を使う。

### OAuth callback API

```text
GET /api/oauth/google/callback
```

Googleから返された `code` と `state` を受け取り、token交換と保存を行う。

受け取るquery parameter:

| パラメータ | 必須 | 内容 |
| --- | --- | --- |
| `code` | 必須 | Googleが返す認可コード |
| `state` | 必須 | OAuth開始時に生成した検証用値 |
| `error` | 任意 | Google同意画面で拒否された場合などのエラー |

処理内容:

- `error` がある場合はtoken交換せず失敗扱いにする
- `state` が存在するか確認する
- 保存済みの `state` と一致するか検証する
- `state` が期限切れの場合は失敗扱いにする
- `code` をGoogle token endpointへ送信する
- Googleから返るtoken responseを検証する
- Google UserInfo endpointからメールアドレスを取得する
- `refresh_token` が含まれる場合は暗号化して保存する
- `refresh_token` が含まれない場合は再同意が必要な状態として扱う
- `code` と平文tokenは保存しない
- 成功時はシステム名、実際に許可されたscope、責任者、問い合わせ先を含むHTMLを返す
- 成功時はGoogleアカウント側で連携解除できる旨を表示する
- 失敗時はシステム名、失敗した処理、要求していたscope、エラーID、責任者、問い合わせ先を含むHTMLを返す

Google token endpoint:

```text
POST https://oauth2.googleapis.com/token
```

送信する値:

| パラメータ | 値 |
| --- | --- |
| `client_id` | Google OAuth client ID |
| `client_secret` | Google OAuth client secret |
| `code` | callbackで受け取った認可コード |
| `redirect_uri` | Google Cloud Consoleに登録したcallback URL |
| `grant_type` | `authorization_code` |

## 保存仕様

### 保存するもの

| 項目 | 保存内容 |
| --- | --- |
| 接続ID | OAuth接続を識別するID |
| connection_key | OAuth接続の用途を識別するキー |
| Googleアカウント識別情報 | UserInfo endpointから取得できるメールアドレス |
| scope | Googleが返した許可済みscope |
| token_type | 通常は `Bearer` |
| expires_at | access tokenの期限を計算した日時 |
| encrypted_refresh_token | 暗号化済みrefresh token |
| status | `connected` / `reauth_required` / `error` など |
| created_at | 作成日時 |
| updated_at | 更新日時 |

### 保存しないもの

| 対象 | 理由 |
| --- | --- |
| 認可コード | 使い捨てであり、token交換後は不要 |
| 平文refresh token | 漏えい時の影響が大きい |
| 平文access token | 短命であり、必要時に再発行できる |
| client secret | アプリ設定として環境変数で管理する |
| TOKEN_ENCRYPTION_KEY | DBに保存しない |

### Supabaseテーブル

初期実装では、次の2テーブルを使う。

- `google_oauth_connections`
- `google_oauth_states`

`google_oauth_connections` は、暗号化済みrefresh tokenと接続状態を保存する。

```sql
create table google_oauth_connections (
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
  updated_at timestamptz not null default now()
);
```

`connection_key` は、このOAuth接続が何用の接続かを表す。初期実装では `internal_ga4_search_console` を使う。

同じ `connection_key` と `google_account_email` の組み合わせが既に存在する場合、再連携時は新規作成ではなく既存行を更新する。これにより、同じ用途の連携でも複数のGoogleアカウントのtokenを同時に保持できる。

```sql
create unique index google_oauth_connections_connection_key_google_account_email_key
  on google_oauth_connections (connection_key, google_account_email);
```

`google_account_email` は、どのGoogleアカウントで同意したかを確認するための表示・監査用情報として扱う。同じ `connection_key` 内で接続を識別する保存キーにも使う。メールアドレスは暗号化せずに保存するが、個人情報として扱い、RLSとservice role keyの管理でフロントエンドから直接読ませない。

`google_oauth_states` は、OAuth開始時に生成した `state` をcallback検証まで一時保存する。

```sql
create table google_oauth_states (
  id uuid primary key default gen_random_uuid(),
  state_hash text not null,
  connection_key text not null,
  expires_at timestamptz not null,
  consumed_at timestamptz,
  created_at timestamptz not null default now()
);

create unique index google_oauth_states_state_hash_key
  on google_oauth_states (state_hash);
```

RLSは両テーブルで有効化する。

```sql
alter table google_oauth_connections enable row level security;
alter table google_oauth_states enable row level security;
```

`anon` / `authenticated` 向けのpolicyは作らない。フロントエンドから直接読み書きさせず、バックエンドが `SUPABASE_SERVICE_ROLE_KEY` を使って操作する。

## state管理仕様

`state` はCSRF対策と接続対象の紐づけに使う。

要件:

- 推測困難なランダム値にする
- OAuth開始時に一時保存する
- callbackで必ず検証する
- 一度使ったら無効化する
- 有効期限を持たせる
- `state` に秘密情報を直接入れない
- `state` に紐づく `connection_key` を保存する

保存先はSupabaseの `google_oauth_states` とする。

保存値は平文 `state` ではなく `state_hash` とする。callbackで受け取った `state` を同じ方法でhash化し、保存済みの `state_hash` と照合する。

有効期限は1日を初期値とする。callback検証に成功したら `consumed_at` を記録し、同じ `state` の再利用を拒否する。

バックエンドだけで運用する可能性があるため、フロントエンドのブラウザ状態に強く依存しない方式を優先する。

## callback表示仕様

成功時はHTMLで次の内容を表示する。

```text
Google連携が完了しました。
GA4 / Search Console OAuth連携
Google OAuth認証が完了しました。

許可されたscope
- Google token responseで返されたscope
- 既知scopeは日本語ラベルとscope URLを併記する
- 未知scopeはscope URLを表示する

接続キー
責任者
問い合わせ先

連携を解除したい場合
Googleアカウントの「サードパーティ製アプリとサービスへの接続」から、この連携のアクセス権を削除してください。
```

失敗時はHTMLで次の内容を表示する。エラーIDは内部ログと照合するためのIDであり、token、code、secretは表示しない。

```text
Google連携に失敗しました。
Google OAuth認証を完了できませんでした。
管理者へ下記のエラーIDを連絡してください。

システム名: GA4 / Search Console OAuth連携
失敗した処理: Google OAuth認証
要求していたscope
- `GOOGLE_OAUTH_SCOPES` のscope
エラーID: xxxxxxxx
責任者
問い合わせ先
```

## 暗号化仕様

初期実装では、Pythonの `cryptography` ライブラリが提供する `Fernet` を使う。

方針:

- `refresh_token` は保存前に必ず暗号化する
- 暗号化キーは `TOKEN_ENCRYPTION_KEY` として環境変数で管理する
- 暗号化キーはSupabaseに保存しない
- 初期実装では復号処理を業務機能から呼ばない
- 将来Google APIを呼ぶ場合、復号処理はGoogle APIを呼ぶ直前のバックエンド処理に限定する
- 暗号化・復号処理は専用サービスに閉じ込める
- 将来KMSへ差し替えられるよう、呼び出し側は暗号化方式に依存しない

処理イメージ:

```text
refresh_token
  ↓ TokenCipher.encrypt
encrypted_refresh_token
  ↓ Supabase保存
  ↓ TokenCipher.decrypt
refresh_token
```

公開鍵暗号は初期実装では採用しない。今回の構成では同じバックエンドがtokenを受け取り、保存し、復号してGoogle APIを呼ぶため、公開鍵暗号にしてもバックエンドが秘密情報を持つ点は変わらない。初期実装では構成を単純に保つ。

暗号化済みtokenを外部サーバへ渡し、外部サーバに暗号化キーを持たせる構成は初期実装では採用しない。秘密情報を扱うサーバが増え、暗号化キー管理と監査の責任範囲が広がるため。

## 環境変数

必要な環境変数:

| 変数名 | 用途 |
| --- | --- |
| `GOOGLE_OAUTH_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth client secret |
| `GOOGLE_OAUTH_REDIRECT_URI` | callback URL |
| `GOOGLE_OAUTH_SCOPES` | 要求scope |
| `GOOGLE_OAUTH_SYSTEM_NAME` | callback画面に表示するシステム名 |
| `GOOGLE_OAUTH_OPERATION_NAME` | callback失敗画面に表示する処理名 |
| `TOKEN_ENCRYPTION_KEY` | Fernet暗号化キー |
| `SUPABASE_URL` | Supabase URL |
| `SUPABASE_SERVICE_ROLE_KEY` | バックエンド保存用のSupabase key |
| `GOOGLE_OAUTH_RESPONSIBLE_NAME` | callback画面に表示する責任者名 |
| `GOOGLE_OAUTH_CONTACT` | callback画面に表示する問い合わせ先 |

`SUPABASE_SERVICE_ROLE_KEY` はフロントエンドに渡してはいけない。

## セキュリティ要件

- OAuth callbackでは `state` を必ず検証する
- `redirect_uri` はGoogle Cloud Consoleに登録した値と一致させる
- 本番環境ではHTTPSを使う
- Google OAuth client secretをフロントエンドに渡さない
- Supabase service role keyをフロントエンドに渡さない
- `code`、`access_token`、`refresh_token`、client secret、暗号化キーをログに出さない
- 平文tokenをAPIレスポンスに含めない
- 暗号化済みtokenをAPIレスポンスに含めない
- Supabaseには暗号化済み `refresh_token` だけを保存する
- Supabaseのtoken保存テーブルはフロントエンドから直接読ませない
- scopeは読み取り専用に限定する
- 初期実装では接続解除APIを作らない
- 接続解除が必要な場合は、Googleアカウント側のアプリ連携画面で手動解除する

## エラーハンドリング

主なエラー:

| 状況 | 扱い |
| --- | --- |
| Google同意画面で拒否された | `error` を記録し、接続失敗として扱う |
| `state` がない | 不正なcallbackとして拒否する |
| `state` が一致しない | 不正なcallbackとして拒否する |
| `state` が期限切れ | 再度OAuth開始を促す |
| token交換に失敗 | 接続失敗として扱い、詳細なsecretはログに出さない |
| `refresh_token` が返らない | 再同意が必要な状態として扱う |
| Supabase保存に失敗 | 接続失敗として扱う。平文tokenは保持しない |
| 暗号化に失敗 | 保存せず接続失敗として扱う |

## テスト方針

テストではGoogleやSupabaseへの実通信を避け、外部I/Oをmockする。

優先するテスト:

- OAuth開始APIが必要なパラメータを含むGoogle認証URLを生成する
- OAuth開始APIが `state` を生成・保存する
- callback APIが `state` 不一致を拒否する
- callback APIが `code` をtoken交換処理へ渡す
- `refresh_token` が暗号化されて保存される
- 保存値に平文 `refresh_token` が含まれない
- token交換レスポンスに `refresh_token` がない場合、再認証必要として扱う
- tokenやsecretがレスポンスに含まれない
- 暗号化済みtokenがレスポンスに含まれない
- 暗号化サービスで暗号化した値を復号できる
- `.env` の設定値を使い、手動確認としてtoken交換と暗号化保存を実行できる

## 未決事項

なし。

## 決定済み事項

- OAuthアプリは `Internal` とする
- 初期実装は `refresh_token` の取得、暗号化、保存までとする
- 保存済みtokenを使ったGA4 / Search Console API呼び出しは初期実装に含めない
- 接続確認としてのGA4 / Search Consoleプロパティ一覧取得は初期実装に含めない
- 接続解除APIとGoogle token revokeは初期実装に含めない
- 接続解除が必要な場合は、Googleアカウント側のアプリ連携画面から手動解除する
- 暗号化済みtokenを外部サーバへ返すAPIは作らない
- 暗号化キーはこのバックエンドだけが持つ
- `state` はSupabaseの `google_oauth_states` にhash保存する
- callback成功時はシステム名、実際に許可されたscope、責任者、問い合わせ先を含むHTMLを返す
- callback成功時はGoogleアカウント側で連携解除できる旨を表示する
- callback失敗時はシステム名、失敗した処理、要求していたscope、エラーID、責任者、問い合わせ先を含むHTMLを返す
- Supabaseは `google_oauth_connections` と `google_oauth_states` を使う
- 両テーブルでRLSを有効化し、`anon` / `authenticated` 向けpolicyは作らない
