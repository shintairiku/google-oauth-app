# backend

FastAPI バックエンドの配置先です。

- `app/main.py`: FastAPI アプリのエントリーポイント
- `app/api`: ルーターとエンドポイント
- `app/core`: 設定や共通基盤
- `app/domain`: ドメイン知識
- `app/services`: ユースケース
- `app/infrastructure`: 永続化や外部連携
- `app/schemas`: 入出力スキーマ
- `tests`: バックエンドテスト
- `.python-version`: 利用する Python 系統の基準
- `pyproject.toml`: `uv` で利用する依存管理とテスト設定
- `uv.lock`: `uv` 用のロックファイル
- `Dockerfile`: バックエンド用コンテナ定義
