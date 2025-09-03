#!/usr/bin/env sh
set -e

# Default values
: "${DJANGO_BIND:=0.0.0.0}"
: "${DJANGO_PORT:=8000}"
: "${DJANGO_ASGI_APP:=bioattend.asgi:application}"

echo "[entrypoint] Applying migrations..."
python manage.py migrate --noinput

echo "[entrypoint] Collecting static files..."
python manage.py collectstatic --noinput || true

# Optional: run checks (non-fatal)
python manage.py check || true

echo "[entrypoint] Starting Daphne on ${DJANGO_BIND}:${DJANGO_PORT}"
exec daphne -b "${DJANGO_BIND}" -p "${DJANGO_PORT}" "${DJANGO_ASGI_APP}"
