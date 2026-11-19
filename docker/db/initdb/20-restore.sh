#!/bin/bash
# Restaura el dump de producción (abril 2020) la primera vez que se crea el volumen.
# Lo ejecuta la imagen de PostGIS después de crear las extensiones (10_postgis.sh).
set -euo pipefail

DUMP_FILE="${DUMP_FILE:-/dump/larbit.pgsql}"

if [ ! -s "$DUMP_FILE" ]; then
    echo "[restore] No hay dump en $DUMP_FILE; se usará una base vacía (migrate creará el esquema)."
    exit 0
fi

echo "[restore] Restaurando $DUMP_FILE en $POSTGRES_DB ..."
# - Se omiten los ALTER ... OWNER TO (el rol 'postgres' del servidor original no existe aquí).
# - Los errores por extensiones, el esquema 'tiger' o 'spatial_ref_sys' ya existentes son esperados
#   y no afectan a las tablas de la aplicación, por eso no se usa ON_ERROR_STOP.
grep -v 'OWNER TO' "$DUMP_FILE" \
    | psql -q -v ON_ERROR_STOP=0 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" 2>&1 \
    | grep -E 'ERROR' | sort | uniq -c | sed 's/^/[restore] (ignorado) /' || true

echo "[restore] Reconciliando nombres de migraciones de 'realty' con el repositorio ..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
BEGIN;
-- En producción las migraciones 0002-0004 de realty se generaron con otros nombres;
-- el esquema resultante es idéntico al de las migraciones versionadas 0002-0005.
DELETE FROM django_migrations WHERE app = 'realty' AND name <> '0001_initial';
INSERT INTO django_migrations (app, name, applied) VALUES
    ('realty', '0002_auto_20200204_1947', now()),
    ('realty', '0003_auto_20200206_2138', now()),
    ('realty', '0004_auto_20200206_2246', now()),
    ('realty', '0005_property_radius', now());
COMMIT;
SQL

echo "[restore] Listo: $(psql -tA --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c 'SELECT count(*) FROM auth_user') usuarios, $(psql -tA --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c 'SELECT count(*) FROM realty_property') propiedades."
