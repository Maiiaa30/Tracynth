# Tracynth backend

The API is a Django 5.2 modular monolith. It defaults to SQLite and an in-memory
cache for local development; deployments supply PostgreSQL and Redis URLs.
Set `DJANGO_DEBUG=true` for plain-HTTP localhost development so secure-cookie
defaults do not prevent the browser from returning session and CSRF cookies.

## Local checks

```sh
python -m venv .venv
.venv/bin/pip install -r requirements-dev.lock
.venv/bin/python manage.py migrate
.venv/bin/python manage.py check
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy .
```

On Windows, use `.venv\\Scripts\\python.exe` instead. Runtime containers install
`requirements.lock` and may invoke `sh entrypoint.sh` from `/app/backend`.

Required production inputs are `DJANGO_SECRET_KEY`, `DATABASE_URL`, and
`REDIS_URL` (or explicit `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`). Set
`DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, and secure-proxy settings
to match the single Caddy origin.

Create the first and only initial operator by passing the password through an
environment variable, never an argument:

```sh
TRACYNTH_INITIAL_USERNAME=operator \
TRACYNTH_INITIAL_PASSWORD='a-long-generated-password' \
python manage.py create_initial_user
```

The SPA first requests `GET /api/v1/auth/csrf/`, then supplies the resulting
cookie in `X-CSRFToken` for unsafe requests. There is no registration route.
