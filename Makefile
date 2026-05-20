.PHONY: frontend backend install-frontend install-backend test-backend build-frontend lint-backend lint-frontend lint db-start db-stop db-reset db-lint db-new

frontend:
	cd frontend && bun run dev

backend:
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

install-frontend:
	cd frontend && bun install

install-backend:
	cd backend && uv sync --extra dev

test-backend:
	cd backend && uv sync --extra dev && uv run pytest

build-frontend:
	cd frontend && bun run build

lint-backend:
	cd backend && uv sync --extra dev && uv run ruff check .

lint-frontend:
	cd frontend && bun run lint

lint: lint-backend lint-frontend

db-start:
	bunx supabase start

db-stop:
	bunx supabase stop

db-reset:
	bunx supabase db reset

db-lint:
	bunx supabase db lint --local --fail-on error

db-new:
	test -n "$(name)" || (echo "usage: make db-new name=your_migration_name" && exit 1)
	bunx supabase migration new $(name)
