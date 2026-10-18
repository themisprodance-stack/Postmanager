#!/usr/bin/env sh
# Production entrypoint: one container runs the web app and the scheduler, sharing the same disk.
set -e
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py run_scheduler &
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 2 --timeout 300
