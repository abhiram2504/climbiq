.PHONY: dev down migrate test test-backend test-frontend

dev:
	docker compose up --build

down:
	docker compose down

migrate:
	docker compose run --rm backend alembic upgrade head

test: test-backend test-frontend

test-backend:
	cd backend && python -m pytest

test-frontend:
	cd frontend && npm run test
