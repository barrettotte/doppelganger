.PHONY: \
	dev migrate \
	test test-unit test-integration \
	fmt lint type-check check \
	docker-up docker-down docker-db psql \
	vllm vllm-down vllm-logs \
	frontend-install frontend-dev frontend \
	prepare-audio train-lora transcribe

dev:	migrate
	uv run uvicorn --factory doppelganger.app:create_app --reload --host 0.0.0.0 --port 8000

migrate:	docker-db
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

docker-down:
	docker compose --profile app --profile orpheus down

docker-db:
	docker compose up -d postgres

psql:	docker-db
	docker compose exec postgres psql -U doppelganger -d doppelganger

vllm:
	docker compose --profile orpheus up -d

vllm-down:
	docker compose --profile orpheus down

# FRONTEND

frontend-install:
	cd frontend && pnpm install

frontend-dev:
	cd frontend && pnpm dev

frontend:
	cd frontend && pnpm build

# TRAINING

prepare-audio:
	uv run python scripts/prepare_audio.py $(ARGS)

train-lora:
	uv run python scripts/train_lora.py $(ARGS)

transcribe:
	uv run python scripts/transcribe_audio.py $(ARGS)
