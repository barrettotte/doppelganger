.PHONY: dev fmt lint type-check check test test-unit test-integration migrate docker-up docker-up-full docker-down docker-db logs

dev:
	uv run uvicorn --factory doppelganger.app:create_app --reload --host 0.0.0.0 --port 8000

migrate:
	uv run alembic upgrade head

test:
	uv run pytest tests -v

test-unit:
	uv run pytest tests -v --ignore=tests/integration

test-integration:
	uv run pytest tests/integration -v

# FORMAT / LINT

fmt:
	uv run ruff format src tests

lint:
	uv run ruff check src tests

type-check:
	uv run basedpyright src

check: fmt lint type-check

# DOCKER

docker-up:
	docker compose --profile app up -d

docker-up-full:
	docker compose --profile app --profile observability up -d

docker-down:
	docker compose --profile app --profile observability down

docker-db:
	docker compose up -d postgres

logs:
	docker compose logs -f
