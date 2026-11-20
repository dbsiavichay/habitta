#!/usr/bin/env bash
#
# Despliega Habitta a un tag de la imagen, condicionado al HEALTHCHECK de la imagen, y
# vuelve al tag anterior si el nuevo nunca queda sano.
#
#   scripts/deploy.sh <latest|sha-abc1234>
#
# Lo corre .github/workflows/ci.yml por SSH, y a mano para volver a un build anterior.
# Corre desde /opt/habitta; la ruta en el edge la instala aparte scripts/apply-edge.sh.
#
# Las migraciones las aplica el entrypoint de la imagen al arrancar web.
#
set -euo pipefail

# cron y las sesiones SSH no interactivas traen un PATH mínimo.
PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

TAG="${1:-}"
if ! grep -qE '^(latest|sha-[0-9a-f]{7,40})$' <<< "$TAG"; then
    echo "uso: deploy.sh <latest|sha-abc1234>" >&2
    exit 2
fi

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"
ENV_FILE="${APP_DIR}/.env"

[ -f "$ENV_FILE" ] || { echo "ERROR: falta ${ENV_FILE}. Ver deploy/README.md." >&2; exit 2; }

# El apply.sh del edge crea esta red, pero un deploy con el edge caído no debe fallar por eso.
docker network inspect edge >/dev/null 2>&1 || docker network create edge >/dev/null

read_tag() {
    grep -E '^WEB_TAG=' "$ENV_FILE" | sed -n '1s/^WEB_TAG=//p' || true
}

# Con un archivo temporal y un rename: `sed -i` cambia entre GNU y BSD, y un corte a la
# mitad no puede dejar un .env truncado (aquí viven los secretos).
write_tag() {
    local tmp
    tmp="$(mktemp "${ENV_FILE}.XXXXXX")"
    chmod 600 "$tmp"
    if grep -qE '^WEB_TAG=' "$ENV_FILE"; then
        sed "s|^WEB_TAG=.*|WEB_TAG=$1|" "$ENV_FILE" > "$tmp"
    else
        cat "$ENV_FILE" > "$tmp"
        printf 'WEB_TAG=%s\n' "$1" >> "$tmp"
    fi
    mv "$tmp" "$ENV_FILE"
}

# La imagen declara su HEALTHCHECK; si falta, la imagen está mal construida y aceptarla
# dejaría este control sin efecto. 180 s: el primer arranque migra una base vacía.
wait_healthy() {
    local deadline=$((SECONDS + 180)) cid state
    while [ "$SECONDS" -lt "$deadline" ]; do
        cid="$(docker compose ps -q web 2>/dev/null || true)"
        if [ -n "$cid" ]; then
            state="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}nohealthcheck{{end}}' "$cid" 2>/dev/null || echo starting)"
            case "$state" in
                healthy)       return 0 ;;
                unhealthy)     echo "   web quedó unhealthy."; return 1 ;;
                nohealthcheck) echo "   la imagen no declara HEALTHCHECK; se rechaza."; return 1 ;;
            esac
        fi
        sleep 3
    done
    echo "   Se acabó el tiempo esperando que web quede healthy."
    return 1
}

PREVIOUS_TAG="$(read_tag)"
PREVIOUS_TAG="${PREVIOUS_TAG:-latest}"

echo ">> Desplegando web: ${PREVIOUS_TAG} -> ${TAG}"
write_tag "$TAG"

rollback() {
    echo
    echo "!! Volviendo web a ${PREVIOUS_TAG}."
    docker compose logs --tail 40 web || true
    write_tag "$PREVIOUS_TAG"
    docker compose pull web || true
    docker compose up -d web || true
    if wait_healthy; then
        echo ">> De vuelta en ${PREVIOUS_TAG}; web está healthy."
    else
        echo "!! EL ROLLBACK NO QUEDÓ HEALTHY. HACE FALTA INTERVENIR A MANO."
        docker compose logs --tail 50 web || true
    fi
    exit 1
}

# Desde aquí todo fallo pasa por `rollback`, nunca por `set -e`: un fallo sin manejar
# dejaría en .env un tag que nunca corrió, y el próximo deploy lo tomaría como el anterior.
if ! docker compose pull web; then
    echo "!! No se pudo bajar ${TAG}. ¿Existe en GHCR y el paquete sigue público?"
    echo "!! Nunca hagas docker login ghcr.io en este host: reemplazaría la credencial de Grazia."
    rollback
fi
# db, redis y media sólo se recrean si cambió su definición en compose.yml.
if ! docker compose up -d db redis media; then
    echo "!! No se pudieron levantar db, redis o media."
    rollback
fi
if ! docker compose up -d web; then
    echo "!! No se pudo arrancar web."
    rollback
fi

echo ">> Esperando que web quede healthy..."
wait_healthy || rollback
echo ">> web está healthy en ${TAG}."

# Cada deploy baja una imagen nueva. Se guardan la que corre y la anterior, para que un
# rollback no necesite red, y se borran los demás tags de Habitta. Nunca `prune -a`: también
# borraría las imágenes que Grazia guarda para sus rollbacks.
repository="$(docker compose config --images web | sed -n 1p)"
repository="${repository%:*}"
docker image ls "$repository" --format '{{.Repository}}:{{.Tag}}' \
    | grep -vxF -e "${repository}:${TAG}" -e "${repository}:${PREVIOUS_TAG}" \
    | xargs -r docker image rm >/dev/null 2>&1 || true
# Capas sin tag que dejó el pull.
docker image prune -f >/dev/null 2>&1 || true
