# task.md

## タスク一覧

### タスク名: GA4 / Search Console OAuth連携
- 目的: Google OAuthでGA4 / Search Consoleの読み取り権限を取得し、継続的にデータ取得できる状態を作る。
- 主な実装内容: OAuth開始URL発行、callbackでのcode/state受け取り、codeからtokenへの交換、refresh tokenの暗号化、Supabaseへの保存。
- 完了条件: Google同意画面から認可後、暗号化済みrefresh tokenをSupabaseへ保存できること。
- 備考: 初期実装ではGA4 / Search Console API呼び出し、接続確認、接続解除、Google token revoke、暗号化済みtoken返却APIは作らない。秘密情報、token交換、暗号化、保存はバックエンドに集約する。暗号化はFernetを初期案とし、将来必要に応じてKMS移行を検討する。
