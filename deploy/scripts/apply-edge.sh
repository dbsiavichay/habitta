#!/usr/bin/env bash
#
# Instala la ruta de Habitta en el proxy compartido (edge) y la aplica.
#
#   scripts/apply-edge.sh
#
# El edge (/opt/edge) es de grazia-infra e importa todos los caddy/sites/*.caddy. Su
# apply.sh falla mientras Caddy rechace cualquiera de ellos, y cada deploy de Grazia lo
# corre, así que un habitta.caddy roto en disco bloquearía los deploys de un proyecto que
# no tiene nada que ver. Este script sólo deja un archivo que Caddy aceptó: si rechaza el
# nuevo, vuelve a poner el anterior y aplica otra vez.
#
set -euo pipefail

# cron y las sesiones SSH no interactivas traen un PATH mínimo.
PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EDGE_DIR="${EDGE_DIR:-/opt/edge}"
SOURCE="${APP_DIR}/caddy/habitta.caddy"
TARGET="${EDGE_DIR}/caddy/sites/habitta.caddy"

[ -x "${EDGE_DIR}/apply.sh" ] || { echo "ERROR: no hay proxy edge en ${EDGE_DIR}. Ver deploy/README.md." >&2; exit 2; }

if [ -f "$TARGET" ] && cmp -s "$SOURCE" "$TARGET"; then
    echo ">> edge: habitta.caddy no cambió; nada que aplicar."
    exit 0
fi

backup=""
if [ -f "$TARGET" ]; then
    backup="$(mktemp "${APP_DIR}/.habitta.caddy.XXXXXX")"
    cp "$TARGET" "$backup"
fi

# Se escribe con un nombre que el glob del edge (*.caddy) no toma y luego se renombra, así
# Caddy nunca lee medio archivo.
cp "$SOURCE" "${TARGET}.new"
chmod 644 "${TARGET}.new"
mv "${TARGET}.new" "$TARGET"

if "${EDGE_DIR}/apply.sh"; then
    rm -f "$backup"
    exit 0
fi

echo "!! edge: Caddy rechazó habitta.caddy; se vuelve a poner lo que había." >&2
if [ -n "$backup" ]; then mv "$backup" "$TARGET"; else rm -f "$TARGET"; fi
"${EDGE_DIR}/apply.sh" || echo "!! edge: reaplicar la config anterior también falló. HACE FALTA INTERVENIR A MANO." >&2
exit 1
