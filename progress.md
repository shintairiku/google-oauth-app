# progress.md

## 2026-05-22 13:45
- 変更内容: `.env` に暗号化済みrefresh tokenを設定してGoogle API疎通確認できる手動確認スクリプトを追加した。設定項目 `GOOGLE_OAUTH_ENCRYPTED_REFRESH_TOKEN` も追加した。
- 目的: Supabaseから直接読むのではなく、暗号化済みtokenを明示的に `.env` へ設定して復号・access token再発行・Search Console / GA4 Admin API確認を行うため。
- 影響範囲: 手動確認スクリプト、backend設定、.env.example、詳細設計ドキュメント。
- 関連ファイル: backend/scripts/check_google_oauth_connection.py, backend/app/core/config.py, backend/.env.example, docs/google-oauth-design.md, progress.md
- 未解決事項: 実行結果の確認はこれから行う。
- 次のアクション: Supabase Studioから `encrypted_refresh_token` を `.env` に設定し、`uv run python scripts/check_google_oauth_connection.py` を実行する。

## 2026-05-22 13:07
- 変更内容: OAuth stateの有効期限初期値を10分から1日に変更した。設定、.env.example、仕様書、詳細設計、関連テストを更新した。
- 目的: Google同意操作からcallbackまでの猶予を長くし、社内運用で時間切れになりにくくするため。
- 影響範囲: OAuth stateの期限設定、ドキュメント、テスト。
- 関連ファイル: backend/app/core/config.py, backend/.env.example, backend/tests/test_google_oauth.py, docs/google-oauth-implementation-spec.md, docs/google-oauth-design.md, progress.md
- 未解決事項: 実Google OAuth / Supabaseへの手動接続確認は未実施。
- 次のアクション: 実環境の.envとSupabase migration適用後に、ブラウザで/api/oauth/google/startから手動確認する。

## 2026-05-21 16:58
- 変更内容: Google OAuth開始API、callback API、Fernet暗号化、Google token交換client、Supabase保存repository、OAuth用Supabase migration、OAuth関連テストを実装した。backendの環境変数と依存関係も追加した。
- 目的: 仕様どおり、refresh tokenを取得して暗号化し、Supabaseへ保存できるようにするため。
- 影響範囲: backend API、backend設定、backend依存関係、Supabase migration、backendテスト。
- 関連ファイル: backend/app/api/routes/google_oauth.py, backend/app/api/router.py, backend/app/core/config.py, backend/app/domain/google_oauth.py, backend/app/services/google_oauth_service.py, backend/app/services/token_cipher.py, backend/app/infrastructure/google_oauth_client.py, backend/app/infrastructure/supabase_oauth_repository.py, backend/tests/test_google_oauth.py, backend/pyproject.toml, backend/uv.lock, backend/.env.example, supabase/migrations/20260521164500_google_oauth_connections.sql
- 未解決事項: 実Google OAuth / Supabaseへの手動接続確認は未実施。
- 次のアクション: 実環境の.envとSupabase migration適用後に、ブラウザで/api/oauth/google/startから手動確認する。

## 2026-05-21 16:45
- 変更内容: OAuth連携の詳細設計書を作成し、backendのモジュール構成、責務分割、Supabase migration、state生成、HTMLレスポンス、エラー種別、テスト設計、実装順序を整理した。
- 目的: 実装仕様をFastAPI backendへ実装できる単位に落とし込むため。
- 影響範囲: ドキュメントのみ。アプリケーションコード、DB schema、テストには変更なし。
- 関連ファイル: docs/google-oauth-design.md, docs/google-oauth-implementation-spec.md, progress.md
- 未解決事項: なし。
- 次のアクション: 詳細設計に沿ってSupabase migrationとbackendテストから実装する。

## 2026-05-21 15:33
- 変更内容: state保存先をSupabaseのgoogle_oauth_statesに確定し、callback成功・失敗時のHTML表示、Supabaseテーブル名、RLS方針を実装仕様書に反映した。未決事項はなしとした。
- 目的: 実装着手前の仕様判断を完了させるため。
- 影響範囲: ドキュメントのみ。アプリケーションコード、DB schema、テストには変更なし。
- 関連ファイル: docs/google-oauth-implementation-spec.md, progress.md
- 未解決事項: なし。
- 次のアクション: 実装時は仕様書に沿ってSupabase migration、設定、テストから着手する。

## 2026-05-21 15:24
- 変更内容: 初期実装の対象をrefresh tokenの取得、暗号化、Supabase保存までに限定した。保存済みtokenを使うGoogle API呼び出し、接続確認、接続解除API、Google token revoke、暗号化済みtoken返却APIは初期対象外と明記した。
- 目的: このサーバの初期目的をtoken確保と安全な保存に絞り、秘密情報を他サーバへ広げない方針を明確にするため。
- 影響範囲: ドキュメントのみ。アプリケーションコード、DB schema、テストには変更なし。
- 関連ファイル: docs/google-oauth-implementation-spec.md, task.md, progress.md
- 未解決事項: state保存先、callback後の遷移先、Supabaseの正式schemaとRLSは未決。
- 次のアクション: state保存先、callback成功・失敗時の表示、Supabase migration/RLS方針を仕様として確定する。

## 2026-05-21 15:04
- 変更内容: 実装仕様書の接続識別子をowner_idからconnection_keyへ変更し、社内アプリの初期値をinternal_ga4_search_consoleとした。再連携時は同じconnection_keyの既存接続を更新する方針を追加した。
- 目的: 社内アプリでは「誰の接続か」より「何用の接続か」を識別する方が実態に合うため。
- 影響範囲: ドキュメントのみ。アプリケーションコード、DB schema、テストには変更なし。
- 関連ファイル: docs/google-oauth-implementation-spec.md, progress.md
- 未解決事項: state保存先、callback後の遷移先、Supabaseの正式schemaとRLS、OAuthアプリ公開状態、token revoke方針、接続確認の範囲は未決。
- 次のアクション: 実装前にstate保存方式とcallback後の画面遷移を決める。

## 2026-05-21 14:39
- 変更内容: OAuth連携の実装仕様書を新規作成し、API仕様、保存仕様、state管理、暗号化、環境変数、セキュリティ要件、エラーハンドリング、テスト方針、未決事項を整理した。
- 目的: 会話で決めた方針を、実装時に参照できる具体的な仕様として分離するため。
- 影響範囲: ドキュメントのみ。アプリケーションコード、DB schema、テストには変更なし。
- 関連ファイル: docs/google-oauth-implementation-spec.md, docs/google-oauth-ga4-search-console.md, progress.md
- 未解決事項: owner_idの意味、state保存先、callback後の遷移先、Supabaseの正式schemaとRLS、OAuthアプリ公開状態、token revoke方針、接続確認の範囲は未決。
- 次のアクション: 実装前に未決事項を確定し、仕様に沿ってテストから着手する。

## 2026-05-21 14:36
- 変更内容: GA4 / Search Console OAuth連携について、refresh tokenの保存方針、Fernetによる暗号化方針、セキュリティ方針をdocsへ追記した。あわせて作業単位をtask.mdに記録した。
- 目的: Google認証に任せられる範囲と、自社サービス側で守るべきtoken管理責任を明確にするため。
- 影響範囲: 仕様ドキュメントと作業管理のみ。アプリケーションコード、DB schema、テストには変更なし。
- 関連ファイル: docs/google-oauth-ga4-search-console.md, task.md, progress.md
- 未解決事項: Supabaseの保存テーブル設計、接続単位、stateの保存・検証方法、callback後の遷移先、OAuthアプリ公開状態は未決。
- 次のアクション: 実装着手前に未決事項を決め、関連テスト方針を確認する。

## 2026-05-22 16:18
- 変更内容: OAuth callback後の成功・失敗HTMLを改善し、許可されたアクセス、行わない操作、接続キー、責任者、問い合わせ先を表示するようにした。表示仕様とAPIテストも更新した。
- 目的: 認証した利用者が、認証後に何のアクセスを許可したかを確認でき、失敗時も管理者へ連絡しやすくするため。
- 影響範囲: Google OAuth callback画面、backend設定、OAuth関連テスト、実装仕様書、詳細設計書。
- 関連ファイル: backend/app/api/routes/google_oauth.py, backend/app/core/config.py, backend/.env.example, backend/tests/test_google_oauth.py, docs/google-oauth-implementation-spec.md, docs/google-oauth-design.md, progress.md
- 未解決事項: なし。
- 次のアクション: 実環境でOAuth callback画面を開き、表示する責任者名と問い合わせ先を `.env` の値で運用に合わせる。

## 2026-05-22 17:20
- 変更内容: OAuth callback画面に表示するシステム名と処理名を `.env` 管理できる設定として追加し、成功画面と失敗画面へ表示した。失敗画面では、何の処理が失敗したか、エラーID、責任者、問い合わせ先を表示するようにした。
- 目的: 認証失敗時に利用者がどのシステムのどの処理で失敗したかを把握し、管理者へ連絡しやすくするため。
- 影響範囲: Google OAuth callback画面、backend設定、.env.example、OAuth関連テスト、実装仕様書、詳細設計書。
- 関連ファイル: backend/app/api/routes/google_oauth.py, backend/app/core/config.py, backend/.env.example, backend/tests/test_google_oauth.py, docs/google-oauth-implementation-spec.md, docs/google-oauth-design.md, progress.md
- 未解決事項: なし。
- 次のアクション: 実環境の `.env` で `GOOGLE_OAUTH_SYSTEM_NAME`、`GOOGLE_OAUTH_OPERATION_NAME`、`GOOGLE_OAUTH_RESPONSIBLE_NAME`、`GOOGLE_OAUTH_CONTACT` を運用名に合わせる。

## 2026-05-22 17:44
- 変更内容: OAuth callback成功画面のscope表示を固定文言からGoogle token responseの許可済みscopeに基づく動的表示へ変更した。失敗画面では、token response取得前でも分かるように `GOOGLE_OAUTH_SCOPES` で要求していたscopeを表示するようにした。
- 目的: GA4 / Search Console以外のscopeや将来の用途追加にも、画面表示が固定実装に依存せず対応できるようにするため。
- 影響範囲: Google OAuth callback画面、OAuth callback結果、OAuth service、OAuth関連テスト、実装仕様書、詳細設計書。
- 関連ファイル: backend/app/api/routes/google_oauth.py, backend/app/domain/google_oauth.py, backend/app/services/google_oauth_service.py, backend/tests/test_google_oauth.py, docs/google-oauth-implementation-spec.md, docs/google-oauth-design.md, progress.md
- 未解決事項: なし。
- 次のアクション: 新しいscopeを追加する場合は `GOOGLE_OAUTH_SCOPES` を更新し、必要なら既知scopeの日本語ラベルを追加する。

## 2026-05-25 14:02
- 変更内容: `backend/.dockerignore` に `.env` と `.env.*` を追加した。
- 目的: Dockerビルド時にsecretを含む可能性がある環境変数ファイルがbuild contextへ含まれないようにするため。
- 影響範囲: backend Dockerビルド時の除外ファイル設定のみ。アプリケーション挙動には影響なし。
- 関連ファイル: backend/.dockerignore, progress.md
- 未解決事項: なし。
- 次のアクション: なし。

## 2026-05-25 14:06
- 変更内容: `APP_ENV=production` のときにFastAPIの `/docs`、`/redoc`、`/openapi.json` を無効化するようにした。production時に各URLが404になるテストも追加した。
- 目的: backendを外部公開した場合に、自動生成APIドキュメントとOpenAPI schemaを公開しないようにするため。
- 影響範囲: FastAPIアプリ生成、backend health/API docs関連テスト。
- 関連ファイル: backend/app/main.py, backend/tests/test_health.py, progress.md
- 未解決事項: なし。
- 次のアクション: Vercelなど本番環境では `APP_ENV=production` を設定する。

## 2026-05-25 15:12
- 変更内容: READMEをテンプレート説明からGoogle OAuth token保存用backendの説明へ更新した。目的、構成、API、保存先、暗号化、環境変数、ローカル起動、デプロイ時の注意、secret管理を整理した。
- 目的: リポジトリの用途と運用上の注意点を、初めて読む人が把握できるようにするため。
- 影響範囲: ドキュメントのみ。アプリケーションコード、DB schema、テストには変更なし。
- 関連ファイル: README.md, progress.md
- 未解決事項: なし。
- 次のアクション: なし。

## 2026-05-25 16:12
- 変更内容: OAuth scopeに `openid email` を追加し、Google UserInfo endpointから取得したメールアドレスを `google_oauth_connections.google_account_email` に保存するようにした。関連テスト、README、仕様書も更新した。
- 目的: Supabase上で、どのGoogleアカウントで認証した接続かを確認できるようにするため。
- 影響範囲: Google OAuth scope、Google OAuth client、OAuth service、Supabase保存値、backendテスト、README、OAuth関連ドキュメント。
- 関連ファイル: backend/app/core/config.py, backend/.env.example, backend/app/domain/google_oauth.py, backend/app/infrastructure/google_oauth_client.py, backend/app/services/google_oauth_service.py, backend/app/api/routes/google_oauth.py, backend/tests/test_google_oauth.py, README.md, docs/google-oauth-implementation-spec.md, docs/google-oauth-design.md, docs/google-oauth-ga4-search-console.md, progress.md
- 未解決事項: なし。
- 次のアクション: Vercelの `GOOGLE_OAUTH_SCOPES` に `openid email` を追加し、Google同意画面から再認証する。

## 2026-05-25 16:16
- 変更内容: OAuth callback成功画面に、Googleアカウント側の「サードパーティ製アプリとサービスへの接続」から連携解除できる旨を表示した。関連テスト、README、仕様書も更新した。
- 目的: 接続解除APIを持たない初期実装でも、利用者が連携解除方法を画面上で確認できるようにするため。
- 影響範囲: Google OAuth callback成功画面、backendテスト、README、OAuth関連ドキュメント。
- 関連ファイル: backend/app/api/routes/google_oauth.py, backend/tests/test_google_oauth.py, README.md, docs/google-oauth-implementation-spec.md, docs/google-oauth-design.md, progress.md
- 未解決事項: なし。
- 次のアクション: なし。
