# Despliegue

Cómo corre Habitta en producción: **https://habitta.dbsiavichay.dev**, en el VPS personal
que ya sirve Grazia, el portfolio y Lectio, detrás del **edge** (el Caddy compartido de ese
servidor).

```text
                      :80 :443
  internet ──▶ edge/caddy (TLS) ──┬── habitta.dbsiavichay.dev/media/* ──▶ habitta-media:8080
                /opt/edge         │     (caddy file-server, sólo lectura, sin /files/)
                                  ├── habitta.dbsiavichay.dev/*       ──▶ habitta-web:8000
                                  │     (daphne: HTTP + WebSocket)        ├── db (PostGIS)
                                  │                                       └── redis
                                  └── Grazia, portfolio, Lectio
                        red docker "edge"                red propia de habitta
```

- El edge es de `grazia-infra`: ocupa 80/443, saca los certificados de Let's Encrypt e
  importa un archivo por sitio desde `/opt/edge/caddy/sites/`. Este repo agrega
  `habitta.caddy` ahí y no toca ningún otro archivo.
- `web` y `media` entran a la red `edge` con alias; `db` y `redis` se quedan en la red
  propia del proyecto. Ningún servicio publica puertos.
- **CSS/JS**: los sirve WhiteNoise dentro de `web` (comprimidos en la imagen).
- **Archivos subidos** (`media/`): volumen `habitta_media`. `web` escribe y el sidecar
  `media` lee y sirve; el edge agrega un día de caché. `/media/files/*` (adjuntos que se
  venden) da 404: sólo salen por la vista que cobra.
- El VPS nunca construye: GitHub Actions construye la imagen, la prueba, la publica en GHCR
  y le dice al VPS qué tag bajar.

## Archivos

| En el repo | En el VPS | Qué hace |
|---|---|---|
| `Dockerfile` | — | Imagen de Django; `HEALTHCHECK` contra `/healthz`, que informa el commit |
| `deploy/compose.yml` | `/opt/habitta/compose.yml` | `web`, `media`, `db`, `redis`, con límites de memoria |
| `deploy/.env.example` | `/opt/habitta/.env` | Secretos e integraciones (chmod 600). `WEB_TAG` lo escribe `deploy.sh` |
| `deploy/caddy/habitta.caddy` | `/opt/edge/caddy/sites/habitta.caddy` | Rutas, caché de media, límite de subida |
| `deploy/scripts/deploy.sh` | `/opt/habitta/scripts/deploy.sh` | Deploy de un tag condicionado al healthcheck, con rollback automático |
| `deploy/scripts/apply-edge.sh` | `/opt/habitta/scripts/apply-edge.sh` | Instala `habitta.caddy` en el edge; si Caddy lo rechaza, restaura el anterior |
| `deploy/scripts/seed.sh` | `/opt/habitta/scripts/seed.sh` | Reemplaza base y media con un dump + tar.gz (carga inicial o restauración) |
| `deploy/scripts/backup.sh` | `/opt/habitta/scripts/backup.sh` | Respaldo diario de base y media, 7 días |
| `deploy/ci/` | — | Réplica del Caddyfile del edge y ensayo de la topología (`smoke.sh`) |

## CI/CD

`.github/workflows/ci.yml` corre en cada pull request y en cada push a `master`.

```text
docker         construye la imagen · pruebas dentro de ella (PostGIS) · smoke.sh: compose + Caddy + sondas
deploy config  shellcheck · compose config · caddy validate · caddy fmt

push a master, todo en verde:
publish        publica la imagen que `docker` ensayó: sha-<7> y latest
deploy         ssh: envía deploy/ → deploy.sh sha-<7> → apply-edge.sh → /healthz en vivo con el commit
```

- `publish` sube exactamente la imagen probada (guardada como artefacto), no una reconstrucción.
- `deploy` arranca primero el contenedor y después instala la ruta: un deploy fallido nunca
  toca el edge.
- Las migraciones las aplica el entrypoint de la imagen al arrancar `web`. Si una falla,
  `web` no queda sano y `deploy.sh` vuelve al tag anterior (cada migración es atómica en
  Postgres, así que la que falló no queda a medias).
- Durante un deploy el sitio da 502 unos segundos mientras arranca el contenedor nuevo.

## Configuración y secretos

| Dónde | Qué | |
|---|---|---|
| GitHub → environment `production` | `VPS_HOST`, `VPS_SSH_PORT`, `VPS_USER`, `VPS_SSH_KEY` | Cómo llega CI al VPS. `VPS_USER` es `deploy`. |
| GitHub → `GITHUB_TOKEN` | `packages: write` (sólo el job `publish`) | Publica en `ghcr.io/dbsiavichay/habitta`. |
| VPS `/opt/habitta/.env` | `POSTGRES_PASSWORD`, `SECRET_KEY`, integraciones | Nunca entran a GitHub. |

El paquete de GHCR es público y el VPS lo baja sin credenciales. **Nunca hagas
`docker login ghcr.io` en el VPS**: Docker guarda una credencial por registro y reemplazaría
la que usa Grazia para bajar sus imágenes privadas.

`VPS_SSH_KEY` entra como `deploy`, que está en el grupo `docker`: trátala como una
credencial de root del VPS. Es una llave propia de Habitta, para revocarla sin tocar las
de Grazia ni del portfolio.

## Primer despliegue

El VPS, el usuario `deploy` y el edge ya existen (`grazia-infra`, `docs/DEPLOYMENT.md`).

### 1. DNS

En Spaceship, antes del primer deploy (Caddy pide el certificado en cuanto carga
`habitta.caddy`, y los intentos fallidos topan los límites de Let's Encrypt):

```text
habitta.dbsiavichay.dev   CNAME   dbsiavichay.dev.
```

```bash
dig +short habitta.dbsiavichay.dev   # dbsiavichay.dev. y la IPv4 del VPS
```

### 2. Carpeta y `.env`

```bash
ssh ubuntu@<vps> 'sudo install -d -o deploy -g deploy /opt/habitta'
scp deploy/.env.example deploy@<vps>:/opt/habitta/.env
ssh deploy@<vps> 'cd /opt/habitta && chmod 600 .env \
  && sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$(openssl rand -hex 24)/; s/^SECRET_KEY=.*/SECRET_KEY=$(openssl rand -hex 32)/" .env'
```

Los secretos se generan en el VPS y no pasan por ningún otro lado. Las integraciones (email,
PayPal, Facebook…) se agregan después con `nano /opt/habitta/.env` y un
`docker compose up -d web`.

### 3. Llave SSH para CI y secrets

```bash
ssh-keygen -t ed25519 -f ~/.ssh/habitta_ci -N '' -C 'github-actions@habitta'
ssh deploy@<vps> 'cat >> ~/.ssh/authorized_keys' < ~/.ssh/habitta_ci.pub

R=dbsiavichay/habitta
gh api -X PUT repos/$R/environments/production >/dev/null
gh secret set VPS_HOST     -R $R --env production --body <vps>
gh secret set VPS_SSH_PORT -R $R --env production --body 22
gh secret set VPS_USER     -R $R --env production --body deploy
gh secret set VPS_SSH_KEY  -R $R --env production < ~/.ssh/habitta_ci
```

### 4. Merge y paquete público

Merge a `master` y mira Actions. El primer `publish` crea `ghcr.io/dbsiavichay/habitta`.
Si el paso `deploy` no puede bajar la imagen, el paquete nació privado: hazlo público
(GitHub → Packages → habitta → Package settings → *Change visibility*) y usa *Re-run failed
jobs*. Para comprobarlo sin credenciales:

```bash
DOCKER_CONFIG=$(mktemp -d) docker manifest inspect ghcr.io/dbsiavichay/habitta:latest
```

### 5. Datos

El primer deploy arranca con una base vacía (migrada). Para cargar la copia local, desde la
raíz del repo en la Mac:

```bash
docker compose exec -T db pg_dump -U habitta -d habitta -Fc > /tmp/habitta.dump
COPYFILE_DISABLE=1 tar --no-xattrs --exclude .DS_Store --exclude '._*' -czf /tmp/media.tar.gz -C media .
ssh deploy@<vps> 'mkdir -p /opt/habitta/seed'
scp /tmp/habitta.dump /tmp/media.tar.gz deploy@<vps>:/opt/habitta/seed/
ssh -t deploy@<vps> '/opt/habitta/scripts/seed.sh /opt/habitta/seed/habitta.dump /opt/habitta/seed/media.tar.gz && rm -r /opt/habitta/seed'
```

`seed.sh` pide confirmación, borra las sesiones de la copia y deja los archivos con el
dueño correcto. Después, la contraseña del admin:

```bash
ssh -t deploy@<vps> 'cd /opt/habitta && docker compose exec web python manage.py changepassword <usuario>'
```

### 6. Respaldos

```bash
ssh deploy@<vps> 'mkdir -p /opt/habitta/backups && (crontab -l 2>/dev/null | grep -v habitta/scripts/backup.sh; \
  echo "30 8 * * * /opt/habitta/scripts/backup.sh >> /opt/habitta/backups/backup.log 2>&1") | crontab -'
```

## Día a día

```bash
# en el VPS, como deploy
cd /opt/habitta
docker compose ps                              # estado y salud
docker compose logs -f web                     # logs de Django
./scripts/deploy.sh sha-abc1234                # volver a un build anterior
grep WEB_TAG .env                              # el tag que debería estar corriendo
docker compose exec web python manage.py …     # comandos de Django
./scripts/backup.sh                            # respaldo ahora
cd /opt/edge && docker compose logs -f caddy   # certificados y ruteo
```

Restaurar un respaldo: `./scripts/seed.sh backups/db_<fecha>.dump backups/media_<fecha>.tar.gz`.

## Verificar un deploy

```bash
curl -s https://habitta.dbsiavichay.dev/healthz                         # {"status": "ok", "sha": "<commit>"}
curl -sI http://habitta.dbsiavichay.dev/ | head -1                      # 308 a https
curl -sI https://habitta.dbsiavichay.dev/static/css/habitta.css | head -1
curl -sI https://habitta.dbsiavichay.dev/media/files/x | head -1        # 404
```

## Ensayar en local

Antes de cambiar el Dockerfile, `compose.yml`, `habitta.caddy` o un script:

```bash
docker build -t ghcr.io/dbsiavichay/habitta:smoke --build-arg GIT_SHA="$(git rev-parse HEAD)" .
EXPECT_SHA="$(git rev-parse HEAD)" deploy/ci/smoke.sh
```

Corre como el proyecto `habitta-smoke` (nunca `habitta`, que en local es el stack de
desarrollo) y lo borra al terminar.

## Compartir el VPS

Grazia es la producción de un cliente y corre en el mismo servidor, detrás del mismo edge.

- **Nunca** `docker login ghcr.io`, `docker image prune -a`, `docker system prune -a`, ni
  `-v`/`--volumes` en un `down` o un `prune`: borrarían imágenes o datos de otros proyectos.
- **Nunca** agregar `ports:` a `db` o `redis`: los puertos de Docker se saltan ufw.
- **Nunca** borrar el volumen `edge_caddy_data`: tiene los certificados de todos los sitios.
- Los deploys de Grazia corren `/opt/edge/apply.sh`, que falla si Caddy rechaza cualquier
  sitio. Por eso `apply-edge.sh` sólo deja un `habitta.caddy` que Caddy aceptó, y CI lo
  valida antes. Evita mergear un cambio de `habitta.caddy` mientras despliega Grazia.
- `deploy/ci/Caddyfile` copia el snippet `security` del edge: si `grazia-infra` lo cambia,
  copia el cambio.
- Habitta usa como máximo ~1.1 GB (web 512M, db 512M, media 64M, redis 64M) de los 3.7 GB
  del VPS, que no tiene swap.

## Quitar Habitta

Primero desactiva el workflow (Actions → *ci* → *Disable workflow*) o el próximo push lo
vuelve a desplegar. Luego, en el VPS como `deploy`, saca la ruta del edge antes de bajar
los contenedores:

```bash
rm /opt/edge/caddy/sites/habitta.caddy && /opt/edge/apply.sh
cd /opt/habitta && docker compose down        # sin -v: los volúmenes quedan
```

Los volúmenes `habitta_pgdata` y `habitta_media` se borran aparte y a propósito
(`docker volume rm`, después de un respaldo). También: la línea del cron, la llave
`github-actions@habitta` en `~/.ssh/authorized_keys`, `/opt/habitta` y el registro DNS.
