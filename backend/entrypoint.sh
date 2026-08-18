#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py check --deploy
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers "${GUNICORN_WORKERS:-3}" --timeout "${GUNICORN_TIMEOUT:-120}"
