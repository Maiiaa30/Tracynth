# syntax=docker/dockerfile:1.7

FROM python:3.15-slim-bookworm AS wheels

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY backend/pyproject.toml backend/requirements.lock ./
RUN python -m pip wheel --wheel-dir /wheels --requirement requirements.lock

COPY backend/ ./backend/
RUN python -m pip wheel --wheel-dir /wheels --no-deps ./backend

FROM python:3.15-slim-bookworm AS runtime

ARG APP_UID=10001
ARG APP_GID=10001

ENV DJANGO_SETTINGS_MODULE=config.settings \
    HOME=/home/tracynth \
    PATH=/home/tracynth/.local/bin:${PATH} \
    PYTHONPATH=/app/backend \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid "${APP_GID}" --system tracynth \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" --system \
        --create-home --home-dir /home/tracynth --shell /usr/sbin/nologin tracynth \
    && install --directory --owner=tracynth --group=tracynth \
        /app /var/lib/tracynth/evidence /var/lib/tracynth/tmp

COPY --from=wheels /wheels /wheels
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels \
        tracynth-backend==0.1.0 \
    && rm -rf /wheels

WORKDIR /app
COPY --chown=tracynth:tracynth backend/ ./backend/
COPY --chown=root:root scripts/healthcheck.py /usr/local/bin/tracynth-healthcheck
COPY --chown=root:root scripts/celery_healthcheck.py /usr/local/bin/tracynth-celery-healthcheck

WORKDIR /app/backend
USER tracynth:tracynth
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "/usr/local/bin/tracynth-healthcheck", "url", "http://localhost:8000/health/"]

CMD ["gunicorn", "config.wsgi:application", "--bind=0.0.0.0:8000", "--workers=3", "--threads=2", "--timeout=60", "--graceful-timeout=30", "--error-logfile=-"]
