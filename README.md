# web-app-standard

`FastAPI` + `Next.js` を前提にした、Web アプリ開発用の基盤リポジトリである。  
`backend` と `frontend` を分けたモノレポ構成を採用し、最小限の API、画面、Docker 起動構成を含んでいる。

## 最初にやること

最初の確認は Docker で行うのが分かりやすい。

1. `docker compose up --build` を実行する
2. `http://localhost:3000` を開いてフロントエンドが表示されることを確認する
3. `http://localhost:8000/docs` を開いて FastAPI の Swagger UI が表示されることを確認する
4. 必要なら `http://localhost:8000/api/health` を開いてヘルスチェックを確認する

まずはこの状態を作れれば、基盤としては正常に動いていると判断できる。

## 全体構成

このリポジトリは、アプリケーション開発を始めるための共通土台として使うものである。  
構成の中心は次の 4 つである。

- `frontend`
  Next.js によるフロントエンドである。画面表示と API 呼び出しを担当する。
- `backend`
  FastAPI によるバックエンドである。API 提供と業務ロジックの配置先である。
- `supabase`
  Supabase CLI を前提としたデータベース migration 基盤である。ローカル DB 設定、migration、seed を管理する。
- `.github/workflows`
  GitHub Actions による最小 CI を置く。backend の lint / test、frontend の lint / build、migration 整合性確認を担う。

技術前提は以下である。

- バックエンドは `FastAPI`
- フロントエンドは `Next.js`
- Python の環境管理は `uv`
- JavaScript の環境管理は `bun`
- データベース基盤は `Supabase`
- 全体起動は `Docker Compose`

最小構成として、以下を含んでいる。

- FastAPI の最小 API
- `/api/health` のヘルスチェック
- Next.js の最小トップページ
- フロントエンドからバックエンドの疎通を確認する表示
- GitHub Actions による最小 CI
- PR テンプレート
- `ruff` と `biome` による lint
- Supabase を前提にした最小のデータベース基盤

## 役割

### `frontend`

- 画面表示を担う
- `backend` の API を呼び出す
- `frontend/src/app` を起点にページを構成する
- `frontend/src/features` に画面ごとの機能を追加していく

### `backend`

- API を提供する
- 業務ロジックを保持する
- `backend/app/api` にエンドポイントを置く
- `backend/app/domain` と `backend/app/services` に業務知識を追加していく

### `supabase`

- ローカル Supabase の設定を持つ
- migration と seed を管理する
- アプリケーション固有の DB 変更を SQL として積み上げる

### `.github/workflows`

- 基盤として最低限必要な CI を持つ
- 開発初期段階で build / test / migration の破綻を早期に検知する

## 起動方法

### Docker で起動する

前提:

- Docker
- Docker Compose

リポジトリのルートで以下を実行する。

```bash
docker compose up --build
```

起動後の確認先:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/api/health`

停止:

```bash
docker compose down
```

Dockerfile や依存関係を変更した場合は、再度 `docker compose up --build` を実行する。

補足:

- `docker compose up --build` で起動するのは `frontend` と `backend` である
- `Supabase` のローカル DB は別に `make db-start` で起動する

この分離にしている理由は、Supabase CLI 自体が内部で Docker を使って複数のサービスを管理するためである。  
`docker-compose.yml` に無理に同居させることも可能ではあるが、CLI 前提の migration 運用とぶつかりやすいため、この基盤では分けている。

### ローカルで個別起動する

Docker を使わずに個別起動したい場合は、ルートの [Makefile](/home/takagi/web-app-standard/Makefile) を使う。  
`make frontend` と `make backend` はどちらもフォアグラウンドで起動するため、ログをそのまま確認しやすい構成である。

前提:

- `uv`
- `bun`

初回セットアップ:

```bash
make install-backend
make install-frontend
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

起動:

```bash
make backend
make frontend
```

`make backend` と `make frontend` は別ターミナルで実行する。  
どちらもフォアグラウンドで起動するため、1つ目のコマンドを実行した端末はそのまま占有される。

利用できる主なコマンド:

- `make backend`
  FastAPI をローカル起動する
- `make frontend`
  Next.js をローカル起動する
- `make install-backend`
  `uv sync --extra dev` でバックエンド依存を同期する
- `make install-frontend`
  `bun install` でフロントエンド依存をインストールする
- `make test-backend`
  バックエンドテストを実行する
- `make build-frontend`
  フロントエンドをビルドする
- `make lint-backend`
  `ruff` でバックエンドを lint する
- `make lint-frontend`
  `biome` でフロントエンドを lint する
- `make lint`
  backend / frontend の lint をまとめて実行する
- `make db-start`
  Supabase のローカルスタックを起動する
- `make db-stop`
  Supabase のローカルスタックを停止する
- `make db-reset`
  migration と seed をローカル DB に再適用する
- `make db-lint`
  ローカル DB の schema を lint する
- `make db-new name=...`
  新しい migration ファイルを作成する

`make db-*` は Supabase CLI を内部で呼び出し、Docker を使ってローカル DB 環境を扱う。  
初回はイメージ取得のため時間がかかることがある。

## このリポジトリの使い方

このリポジトリは、個別のアプリケーションを作るための出発点として、Template Repository として使う想定である。

新しいアプリケーションごとに独立した履歴で始めたい場合は、GitHub の Template Repository として使うのが適している。

流れ:

1. このリポジトリを GitHub で Template Repository に設定する
2. `Use this template` から新しいリポジトリを作成する
3. 作成された新しいリポジトリ側で、要件に応じた実装を追加する

向いているケース:

- アプリケーションごとに履歴を完全に分けたい
- この基盤リポジトリ自体にはアプリ固有の変更を混ぜたくない
- 毎回クリーンな初期状態から始めたい

## CI と PR テンプレート

GitHub 用の最小構成として、以下を含んでいる。

- `.github/workflows/ci.yml`
  `backend` の lint / test、`frontend` の lint / build、Supabase migration の整合性確認を実行する
- `.github/pull_request_template.md`
  PR 作成時の記入項目を揃える

このため、Template Repository として利用した場合でも、新しく作成したリポジトリには最初から CI と PR テンプレートが入る。

## Docker 構成

全体の起動定義は [docker-compose.yml](/home/takagi/web-app-standard/docker-compose.yml) にある。

### `frontend`

- `frontend/Dockerfile` から作成されるコンテナ
- `bun` を使って Next.js アプリを起動する
- ホストの `3000` 番ポートで公開する

役割:

- 画面表示
- バックエンド API の呼び出し

### `backend`

- `backend/Dockerfile` から作成されるコンテナ
- `uv` を使って FastAPI アプリを起動する
- ホストの `8000` 番ポートで公開する

役割:

- API 提供
- 業務ロジックの配置先
- 今後の DB や外部サービス連携の中心

### サービス間通信

- ブラウザからは `http://localhost:3000` と `http://localhost:8000` を利用する
- `frontend` コンテナから `backend` へは `http://backend:8000` で接続する

つまり、ブラウザから見る URL と、コンテナ同士で通信する URL は異なる。

## データベース構成

データベース基盤として `Supabase` を前提にしている。  
ただし、このリポジトリにはアプリケーション固有のテーブル設計は含めず、あくまで migration とローカル開発の型だけを置く方針である。

ローカル DB 運用の基本:

- `supabase/config.toml`
  ローカル Supabase の設定
- `supabase/migrations/`
  マイグレーション SQL の配置先
- `supabase/seed.sql`
  ローカル用 seed データの配置先

基本的な流れ:

1. `make db-start` で Supabase ローカル環境を起動する
2. `make db-new name=...` で migration を作成する
3. `make db-reset` で migration を適用し直す
4. `make db-lint` で schema の lint を確認する

`db-start` `db-stop` `db-reset` `db-lint` は、内部的には Supabase CLI と Docker を利用する。

## ローカルから本番へ反映する流れ

Supabase の DB 変更は、基本的には次の流れで扱う。

1. ローカルで `make db-start` を実行する
2. `supabase/migrations/` に migration を追加する
3. `make db-reset` と `make db-lint` でローカル検証する
4. 変更を GitHub に push する
5. CI で migration 整合性を確認する
6. 本番反映時は、対象の Supabase プロジェクトに対して `supabase db push` を実行する

ローカルからリモート Supabase へ反映する前提コマンドは以下である。

```bash
supabase login
supabase link --project-ref <PROJECT_ID>
supabase db push
```

`PROJECT_ID` は Supabase ダッシュボードの URL から確認できる。  
本番環境への反映は、ローカル端末から手動で実行するより、GitHub Actions などの CI/CD パイプラインから実行する方が安全である。

## ディレクトリ構成

```text
.
├── backend/
│   ├── .python-version
│   ├── Dockerfile
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── domain/
│   │   ├── infrastructure/
│   │   ├── schemas/
│   │   └── services/
│   ├── pyproject.toml
│   ├── uv.lock
│   └── tests/
├── .github/
│   └── workflows/
├── docs/
├── supabase/
│   ├── config.toml
│   ├── migrations/
│   ├── seed.sql
│   └── README.md
├── frontend/
│   ├── Dockerfile
│   ├── .env.example
│   ├── biome.json
│   ├── bun.lock
│   ├── package.json
│   ├── public/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   ├── lib/
│   │   └── styles/
│   └── tests/
├── docker-compose.yml
├── Makefile
├── .editorconfig
├── progress.md
├── task.md
└── README.md
```

## 主な配置先

### `backend/`

FastAPI 側の実装を配置する。

- `backend/app/main.py`
  FastAPI アプリのエントリーポイント
- `backend/app/api`
  ルーター、エンドポイント
- `backend/app/core`
  設定、共通処理
- `backend/app/domain`
  ドメイン知識、業務ルール
- `backend/app/services`
  ユースケース、アプリケーションサービス
- `backend/app/infrastructure`
  DB、外部サービス連携
- `backend/app/schemas`
  リクエスト、レスポンスの型
- `backend/tests`
  バックエンドテスト
- `backend/.python-version`
  利用する Python 系統の基準
- `backend/uv.lock`
  `uv` 用のロックファイル

### `frontend/`

Next.js 側の実装を配置する。

- `frontend/src/app`
  ページ、レイアウト、ルーティング
- `frontend/src/components`
  再利用 UI
- `frontend/src/features`
  機能単位の UI とロジック
- `frontend/src/lib`
  共通関数、API クライアント
- `frontend/src/styles`
  スタイル定義
- `frontend/public`
  静的ファイル
- `frontend/tests`
  フロントエンドテスト
- `frontend/.env.example`
  フロントエンド用の環境変数サンプル
- `frontend/biome.json`
  `biome` の設定
- `frontend/bun.lock`
  `bun` 用のロックファイル

### `docs/`

作成したいアプリケーションの仕様書や補足資料を置く場所である。  
この基盤リポジトリでは最小限の構成だけを用意し、詳細な中身は派生先で追加する想定である。

### `supabase/`

Supabase CLI と migration を配置する。

- `supabase/config.toml`
  ローカル Supabase の設定
- `supabase/migrations`
  migration SQL の配置先
- `supabase/seed.sql`
  ローカル seed データ

### ルート

- `.github/workflows/ci.yml`
  GitHub Actions の CI 定義
- `.github/pull_request_template.md`
  PR テンプレート
- `.editorconfig`
  エディタ共通設定
- `Makefile`
  ローカル実行と補助コマンド

## 開発の進め方

一般的には次の順で進める想定である。

1. `docker compose up --build` で起動確認する
2. `make lint` で lint が通る状態を保つ
3. `backend/app/domain` と `backend/app/services` に業務ロジックを追加する
4. `frontend/src/features` に画面ごとの機能を追加する
5. `docs/` に仕様や設計判断を残す

Docker を使わずに進めたい場合は、`make backend` と `make frontend` を別ターミナルで実行する。

## この基盤に含めていないもの

以下はアプリケーションごとに変わるため、このリポジトリでは固定していない。

- 認証
- リモート Supabase プロジェクト設定
- ORM
- UI ライブラリ
- deploy 設定
- lint / formatter の詳細ルール設計
