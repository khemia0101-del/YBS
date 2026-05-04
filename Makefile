.PHONY: up down build migrate rollback test seed logs shell lint format check

# ── Docker ────────────────────────────────────────────────────────────────────
up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build

restart:
	docker-compose restart api worker

logs:
	docker-compose logs -f api worker beat

# ── Database ──────────────────────────────────────────────────────────────────
migrate:
	docker-compose exec api alembic upgrade head

rollback:
	docker-compose exec api alembic downgrade -1

migration:
	docker-compose exec api alembic revision --autogenerate -m "$(name)"

db-shell:
	docker-compose exec db psql -U ybs ybs_os

# ── Testing ───────────────────────────────────────────────────────────────────
test:
	docker-compose exec api pytest tests/ -v --tb=short

test-unit:
	docker-compose exec api pytest tests/unit/ -v

test-integration:
	docker-compose exec api pytest tests/integration/ -v

test-acceptance:
	docker-compose exec api pytest tests/acceptance/ -v

test-coverage:
	docker-compose exec api pytest tests/ --cov=app --cov-report=html

# ── Development ───────────────────────────────────────────────────────────────
seed:
	docker-compose exec api python scripts/seed_dev_data.py

shell:
	docker-compose exec api python

api-shell:
	docker-compose exec api bash

# ── Code Quality ──────────────────────────────────────────────────────────────
lint:
	docker-compose exec api ruff check app/ tests/

format:
	docker-compose exec api ruff format app/ tests/

check:
	docker-compose exec api ruff check app/ tests/ && docker-compose exec api mypy app/

# ── Frontend ──────────────────────────────────────────────────────────────────
frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

frontend-test:
	cd frontend && npm test
