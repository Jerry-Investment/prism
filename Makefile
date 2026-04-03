.PHONY: help up down dev test lint build logs

help:
	@echo "PRISM — Available commands:"
	@echo "  make up       Start all services (dev mode with hot-reload)"
	@echo "  make down     Stop and remove containers"
	@echo "  make dev      Start backend + frontend in dev mode"
	@echo "  make test     Run backend tests in isolated containers"
	@echo "  make lint     Run backend (ruff) + frontend (eslint) linters"
	@echo "  make build    Build all Docker images"
	@echo "  make logs     Tail all service logs"
	@echo "  make db-init  Re-run DB init SQL"
	@echo "  make shell    Open backend shell"

up:
	docker compose up -d

down:
	docker compose down

dev:
	docker compose up backend worker frontend --build

test:
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit backend_test

lint:
	cd backend && pip install ruff --quiet && ruff check app/ tests/
	cd frontend && npm run lint

build:
	docker compose build

logs:
	docker compose logs -f

db-init:
	docker compose exec db psql -U prism -d prism -f /docker-entrypoint-initdb.d/01_init.sql

shell:
	docker compose exec backend bash
