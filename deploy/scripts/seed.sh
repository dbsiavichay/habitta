#!/usr/bin/env bash
#
# Carga una copia completa de datos: un pg_dump en formato custom y un tar.gz de media/.
# REEMPLAZA la base `habitta` y todos los archivos subidos.
#
#   scripts/seed.sh <habitta.dump> <media.tar.gz>
#
# Sirve para la carga inicial (desde la base local, ver deploy/README.md) y para restaurar
# un respaldo de scripts/backup.sh (backups/db_*.dump + backups/media_*.tar.gz).
#
set -euo pipefail

PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

if [ "$#" -ne 2 ]; then
    echo "uso: seed.sh <habitta.dump> <media.tar.gz>" >&2
    exit 2
fi
DUMP="$(realpath "$1")"
MEDIA_TAR="$(realpath "$2")"
[ -s "$DUMP" ] || { echo "ERROR: ${DUMP} no existe o está vacío." >&2; exit 2; }
[ -s "$MEDIA_TAR" ] || { echo "ERROR: ${MEDIA_TAR} no existe o está vacío." >&2; exit 2; }
gzip -t "$MEDIA_TAR" || { echo "ERROR: ${MEDIA_TAR} no es un tar.gz válido." >&2; exit 2; }

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"
# Sin .env no es un despliegue: en un checkout del repo el proyecto también se llama
# `habitta` y esto borraría la base de desarrollo.
[ -f .env ] || { echo "ERROR: falta ${APP_DIR}/.env; esto se corre en /opt/habitta." >&2; exit 2; }

echo "Esto BORRA la base 'habitta' y todo media/ en este servidor y los reemplaza con:"
echo "  ${DUMP}"
echo "  ${MEDIA_TAR}"
read -r -p "Escribe 'habitta' para seguir: " answer
[ "$answer" = "habitta" ] || { echo "Cancelado."; exit 1; }

# psql por TCP con la contraseña del contenedor, sin depender de la regla `trust` del socket.
psql_db() {
    docker compose exec -T db sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" "$@"' sh "$@"
}

echo ">> Levantando db"
docker compose up -d --wait db

echo ">> Deteniendo web (nadie escribe mientras se restaura)"
docker compose stop web

echo ">> Base: recreando y restaurando"
psql_db dropdb -h 127.0.0.1 -U habitta --if-exists --force habitta
psql_db createdb -h 127.0.0.1 -U habitta -O habitta habitta
# --no-owner/--no-acl: los objetos quedan del usuario habitta, venga de donde venga el dump.
# Las extensiones (postgis, topology, tiger) vienen en el dump.
psql_db pg_restore -h 127.0.0.1 -U habitta -d habitta --no-owner --no-acl --exit-on-error < "$DUMP"
# Las sesiones de la copia no sirven (otra SECRET_KEY) y no deben viajar.
psql_db psql -h 127.0.0.1 -U habitta -d habitta -q -c 'DELETE FROM django_session;'

echo ">> Media: vaciando y extrayendo (como el usuario app de la imagen)"
docker compose run --rm --no-deps -T \
    -v "${MEDIA_TAR}:/seed/media.tar.gz:ro" \
    --entrypoint sh web -c '
        set -e
        find /app/media -mindepth 1 -delete
        tar -xzf /seed/media.tar.gz -C /app/media --no-same-owner
        echo "   $(find /app/media -type f | wc -l) archivos, $(du -sh /app/media | cut -f1)"
    '

echo ">> Arrancando web (el entrypoint aplica las migraciones que falten)"
docker compose up -d --wait --wait-timeout 180 web
docker compose exec -T web python manage.py shell -v 0 -c \
    "from django.contrib.auth.models import User; from apps.realty.models import Property; print(f'   {User.objects.count()} usuarios, {Property.objects.count()} anuncios')"
echo ">> Listo."
