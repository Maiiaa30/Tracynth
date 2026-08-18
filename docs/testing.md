# Testing

Tests use synthetic fixtures, reserved/example domains, mocked network and DNS
responses, and controlled local files. The default suite never depends on an
arbitrary live service. Optional live integration tests must be explicitly
selected and remain safe, passive, and bounded.

## Backend

```bash
python -m pip install -e "./backend[dev]"
cd backend
python -m ruff format --check .
python -m ruff check .
python -m mypy .
cd ..
python backend/manage.py makemigrations --check --dry-run
cd backend && python -m pytest --cov=. --cov-report=term-missing
```

Backend coverage emphasizes authentication/session behavior, permissions,
collector normalization and isolation, state transitions, SSRF edge cases,
crawl budgets, file/archive defenses, sanitization immutability, relationship
provenance, import deletion/redaction, monitoring changes, and report redaction.

## Frontend

```bash
cd frontend
npm ci
npm run format:check
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

Critical flows are tested with accessible roles and labels rather than styling
selectors. Browser end-to-end tests cover login, mocked scan creation and result
review, safe file analysis, identity review, evidence access, and logout.

## Deployment

```bash
cp .env.example .env
docker compose config --quiet
docker compose build
```

Before release, also run dependency and secret scanners available in the
environment, review candidates manually, run Django's deployment checks under
production-like settings, apply migrations to a clean PostgreSQL database, and
exercise a clean Compose startup and health checks.
