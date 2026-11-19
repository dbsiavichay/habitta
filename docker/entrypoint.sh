#!/bin/sh
set -e

# Espera a que la base de datos acepte conexiones.
echo "Esperando a la base de datos..."
python - <<'PY'
import sys, time
import django
django.setup()
from django.db import connection
for attempt in range(60):
    try:
        connection.ensure_connection()
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(f"  BD no disponible ({exc.__class__.__name__}), reintentando...", flush=True)
        time.sleep(2)
sys.exit("La base de datos no respondió a tiempo")
PY

if [ "${DJANGO_MIGRATE:-1}" = "1" ]; then
    python manage.py migrate --noinput
fi

exec "$@"
