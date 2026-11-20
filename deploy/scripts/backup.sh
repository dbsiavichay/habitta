#!/usr/bin/env bash
#
# Respaldo diario: pg_dump de la base y un tar.gz del volumen de media. Se guardan 7 días.
# Los dos archivos de una misma fecha se restauran con scripts/seed.sh.
#
# Se instala en el cron del usuario `deploy` (ver deploy/README.md). El host corre en UTC:
# 08:30 UTC son las 03:30 en Ecuador (sin horario de verano). Grazia respalda a las 08:15.
#   30 8 * * * /opt/habitta/scripts/backup.sh >> /opt/habitta/backups/backup.log 2>&1
#
# Protege de lo probable (un error humano, un volumen recreado), no de perder el VPS: para
# eso hay que copiar backups/ fuera del servidor (ver el final de este archivo).
#
set -euo pipefail

PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"
[ -f .env ] || { echo "ERROR: falta ${APP_DIR}/.env; esto se corre en /opt/habitta." >&2; exit 2; }

BACKUP_DIR="${APP_DIR}/backups"
# compose.yml fija `name: habitta`, que prefija los volúmenes.
MEDIA_VOLUME="habitta_media"
RETENTION_DAYS=7
STAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"

FREE_MB="$(df -Pm "$BACKUP_DIR" | awk 'NR==2 {print $4}')"
if [ "$FREE_MB" -lt 2048 ]; then
    echo "AVISO: sólo quedan ${FREE_MB} MB libres en el disco de respaldos." >&2
fi

# --- Base de datos -------------------------------------------------------------
# --format=custom ya va comprimido: no se pasa por gzip.
echo ">> [$(date +%FT%T%z)] pg_dump"
DB_TMP="${BACKUP_DIR}/.db_${STAMP}.dump.partial"
DB_OUT="${BACKUP_DIR}/db_${STAMP}.dump"
docker compose exec -T db sh -c \
    'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -h 127.0.0.1 -U habitta -d habitta --format=custom' \
    > "$DB_TMP"
[ -s "$DB_TMP" ] || { echo "ERROR: pg_dump dejó un archivo vacío." >&2; rm -f "$DB_TMP"; exit 1; }
mv "$DB_TMP" "$DB_OUT"

# --- Media ---------------------------------------------------------------------
# Fotos, portadas, avatares y adjuntos. Sus filas viven en Postgres; restaurar la base sin
# esto deja imágenes rotas en todo el sitio.
echo ">> [$(date +%FT%T%z)] tar de media"
MEDIA_TMP="${BACKUP_DIR}/.media_${STAMP}.tar.gz.partial"
docker run --rm \
    -v "${MEDIA_VOLUME}:/data:ro" \
    -v "${BACKUP_DIR}:/backup" \
    alpine:3 tar czf "/backup/$(basename "$MEDIA_TMP")" -C /data .
mv "$MEDIA_TMP" "${BACKUP_DIR}/media_${STAMP}.tar.gz"

# --- Retención -----------------------------------------------------------------
echo ">> Borrando respaldos de más de ${RETENTION_DAYS} días"
find "$BACKUP_DIR" -maxdepth 1 -name 'db_*.dump'      -mtime "+${RETENTION_DAYS}" -delete
find "$BACKUP_DIR" -maxdepth 1 -name 'media_*.tar.gz' -mtime "+${RETENTION_DAYS}" -delete

# --- Copia fuera del VPS ---------------------------------------------------------
# Para activarla: instalar rclone, configurar un remoto (Cloudflare R2, S3, Google Drive),
# exportar RCLONE_REMOTE y descomentar:
#
# if command -v rclone >/dev/null 2>&1 && [ -n "${RCLONE_REMOTE:-}" ]; then
#     rclone copy "$BACKUP_DIR" "${RCLONE_REMOTE}:habitta/$(hostname -s)" \
#         --include 'db_*.dump' --include 'media_*.tar.gz'
# fi

echo ">> [$(date +%FT%T%z)] listo: $(basename "$DB_OUT"), media_${STAMP}.tar.gz"
