#!/usr/bin/env bash
#
# Ensayo de la topología de producción: deploy/compose.yml (tal cual) + un Caddy que carga
# habitta.caddy con el snippet del edge (deploy/ci/Caddyfile), y pruebas como un visitante.
# Lo corre CI (job `docker`) y se puede correr en local:
#
#   docker build -t ghcr.io/dbsiavichay/habitta:smoke --build-arg GIT_SHA="$(git rev-parse HEAD)" .
#   EXPECT_SHA="$(git rev-parse HEAD)" deploy/ci/smoke.sh
#
# Usa el proyecto de compose `habitta-smoke` (nunca `habitta`: en local ése es el stack de
# desarrollo y sus volúmenes) y lo borra al terminar. KEEP=1 lo deja arriba para revisar.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT="habitta-smoke"
DOMAIN="habitta.dbsiavichay.dev"
CADDY="habitta-smoke-caddy"
CURL_IMAGE="curlimages/curl:8.11.1"
WORK="$(mktemp -d)"

compose() { docker compose -p "$PROJECT" -f "${WORK}/compose.yml" "$@"; }

cleanup() {
    status=$?
    if [ "$status" -ne 0 ]; then
        echo "--- logs de web ---"
        compose logs --tail 60 web 2>/dev/null || true
        echo "--- logs de caddy ---"
        docker logs --tail 30 "$CADDY" 2>/dev/null || true
    fi
    if [ "${KEEP:-0}" = "1" ]; then
        echo ">> KEEP=1: queda arriba. Para bajar: docker rm -f ${CADDY}; docker compose -p ${PROJECT} -f ${WORK}/compose.yml down -v"
        exit "$status"
    fi
    docker rm -f "$CADDY" >/dev/null 2>&1 || true
    compose down -v --remove-orphans >/dev/null 2>&1 || true
    rm -rf "$WORK"
    exit "$status"
}
trap cleanup EXIT

# compose.yml lee .env de su propia carpeta: se ensaya desde una copia con secretos de mentira.
cp "${ROOT}/deploy/compose.yml" "${WORK}/compose.yml"
printf '%s\n' 'POSTGRES_PASSWORD=smoke' 'SECRET_KEY=smoke-not-a-secret' 'WEB_TAG=smoke' > "${WORK}/.env"

docker network inspect edge >/dev/null 2>&1 || docker network create edge >/dev/null

echo ">> Levantando el stack (${PROJECT})"
compose up -d --wait --wait-timeout 240

echo ">> Levantando el edge de ensayo"
docker rm -f "$CADDY" >/dev/null 2>&1 || true
docker run -d --name "$CADDY" --network edge --network-alias "$DOMAIN" \
    -v "${ROOT}/deploy/ci/Caddyfile:/etc/caddy/Caddyfile:ro" \
    -v "${ROOT}/deploy/caddy:/etc/caddy/sites:ro" \
    caddy:2-alpine >/dev/null

# Archivos de prueba en el volumen, escritos por web como en producción.
compose exec -T web sh -c '
    mkdir -p /app/media/covers /app/media/files
    echo portada > /app/media/covers/smoke.txt
    echo adjunto > /app/media/files/smoke.txt'

curl_edge() { docker run --rm --network edge "$CURL_IMAGE" -sk --max-time 10 "$@"; }

fail=0
check() {
    local name="$1" got="$2" want="$3"
    if printf '%s' "$got" | grep -qiE -- "$want"; then
        echo "   ok   ${name}"
    else
        echo "   FAIL ${name}: se esperaba /${want}/"
        printf '%s\n' "$got" | head -20 | sed 's/^/        /'
        fail=1
    fi
}

echo ">> Esperando el certificado interno de Caddy"
for _ in $(seq 1 30); do
    if curl_edge -f -o /dev/null "https://${DOMAIN}/healthz" 2>/dev/null; then break; fi
    sleep 1
done

echo ">> Pruebas"
health="$(curl_edge "https://${DOMAIN}/healthz")"
check "healthz por el edge" "$health" '"status": ?"ok"'
if [ -n "${EXPECT_SHA:-}" ]; then
    check "healthz reporta el commit" "$health" "\"sha\": ?\"${EXPECT_SHA}\""
fi

check "http redirige a https" "$(curl_edge -o /dev/null -w '%{http_code} %{redirect_url}' "http://${DOMAIN}/")" "^30[18] https://${DOMAIN}/"

home="$(curl_edge -i "https://${DOMAIN}/")"
check "home responde 200" "$home" '^HTTP/[0-9.]+ 200'
check "cabeceras del edge" "$home" '^x-content-type-options: nosniff'
check "un solo HSTS (el del edge)" "$(printf '%s' "$home" | grep -ci '^strict-transport-security' || true)" '^1$'
check "sin cabecera Server" "$(printf '%s' "$home" | grep -ci '^server:' || true)" '^0$'

css="$(curl_edge -I -H 'Accept-Encoding: gzip' "https://${DOMAIN}/static/css/habitta.css")"
check "CSS de WhiteNoise" "$css" '^HTTP/[0-9.]+ 200'
check "CSS comprimido" "$css" '^content-encoding: (gzip|zstd)'

media="$(curl_edge -i "https://${DOMAIN}/media/covers/smoke.txt")"
check "media por el sidecar" "$media" '^portada'
check "media con caché" "$media" '^cache-control: public, max-age=86400'
check "adjuntos bloqueados" "$(curl_edge -o /dev/null -w '%{http_code}' "https://${DOMAIN}/media/files/smoke.txt")" '^404$'
check "sin listado de carpetas" "$(curl_edge -o /dev/null -w '%{http_code}' "https://${DOMAIN}/media/covers/")" '^404$'

admin="$(curl_edge -o /dev/null -w '%{http_code} %{redirect_url}' "https://${DOMAIN}/admin/")"
check "admin pide login" "$admin" '^302 https://'

if [ "$fail" -ne 0 ]; then
    echo "!! El ensayo falló."
    exit 1
fi
echo ">> Ensayo OK."
