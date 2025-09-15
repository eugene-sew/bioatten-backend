#!/usr/bin/env sh
set -e

# Default values
: "${DJANGO_BIND:=0.0.0.0}"
: "${DJANGO_PORT:=8000}"
: "${DJANGO_ASGI_APP:=bioattend.asgi:application}"

echo "[entrypoint] Applying migrations..."
python manage.py migrate --noinput

echo "[entrypoint] Creating superuser..."
python manage.py shell -c "
from authentication.models import User
if not User.objects.filter(email='noah@bioattend.online').exists():
    User.objects.create_superuser(
        email='noah@bioattend.online',
        password='123456',
        first_name='Noah',
        last_name='Admin',
        role='ADMIN'
    )
    print('Superuser created successfully')
else:
    print('Superuser already exists')
"

echo "[entrypoint] Collecting static files..."
python manage.py collectstatic --noinput || true

# Optional: run checks (non-fatal)
python manage.py check || true

echo "[entrypoint] Starting Daphne on ${DJANGO_BIND}:${DJANGO_PORT}"
exec daphne -b "${DJANGO_BIND}" -p "${DJANGO_PORT}" "${DJANGO_ASGI_APP}"
