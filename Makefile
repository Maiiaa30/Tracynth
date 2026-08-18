.PHONY: setup lint format-check typecheck test build compose-check migrate account dev

setup:
	python -m pip install -e "./backend[dev]"
	cd frontend && npm ci

lint:
	cd backend && python -m ruff check .
	cd frontend && npm run lint

format-check:
	cd backend && python -m ruff format --check .
	cd frontend && npm run format:check

typecheck:
	cd backend && python -m mypy .
	cd frontend && npm run typecheck

test:
	cd backend && python -m pytest --cov=. --cov-report=term-missing
	cd frontend && npm test -- --run

build:
	cd frontend && npm run build
	docker compose build

compose-check:
	docker compose config --quiet
	python scripts/check_compose_security.py --compose-file docker-compose.yml

migrate:
	docker compose run --rm backend python manage.py migrate

account:
	docker compose run --rm backend python manage.py create_initial_user

dev:
	docker compose up --build
