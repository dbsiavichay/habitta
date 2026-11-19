# Larbit

Portal de clasificados (inmuebles, servicios y empleos) con mapa, chat en tiempo real,
subastas y pagos (transferencia bancaria y PayPal).

**Stack:** Django 5.2 · Python 3.12 · Django Channels 4 (daphne) · PostgreSQL 17 + PostGIS 3.5 ·
Redis 7 · Django REST Framework.

## Levantar con Docker

```bash
cp .env.example .env.docker      # ajusta los valores (ver abajo)
docker compose up -d --build
```

La app queda en <http://localhost:8000>.

- `docker-compose.override.yml` se aplica automáticamente y activa el modo desarrollo:
  `DEBUG=True`, `runserver` con recarga en caliente y el código montado como volumen.
- El contenedor `web` espera a la base de datos y ejecuta `migrate` al arrancar.
- Para crear un administrador:

  ```bash
  docker compose exec web python manage.py createsuperuser
  ```

### Datos iniciales (dump)

Si existe `backups/larbit27042020.pgsql`, se restaura automáticamente **la primera vez**
que se crea el volumen de la base de datos (`docker/db/initdb/20-restore.sh`). Para usar
otro dump, define `DUMP_PATH=/ruta/al/dump.pgsql` antes de `docker compose up`.

Los archivos subidos por los usuarios viven en `media/` (montado como volumen; no está en git).

Para volver a restaurar desde cero, borra el volumen:

```bash
docker compose down -v && docker compose up -d
```

### Modo producción

Usa sólo el archivo base, sin el override de desarrollo:

```bash
docker compose -f docker-compose.yml up -d --build
```

- Con `DEBUG=False` son obligatorias `SECRET_KEY`, `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`.
- Detrás de un proxy HTTPS activa `SECURE_SSL=True` (cookies seguras, HSTS y redirección a HTTPS).
- Los estáticos los sirve WhiteNoise.
- Los archivos de `media/` deben servirse desde nginx o un storage externo.
  `SERVE_MEDIA=True` permite servirlos desde Django, pero sólo para pruebas.

## Variables de entorno

Todas están documentadas en [`.env.example`](.env.example). Las integraciones externas son
opcionales: si se dejan vacías, la funcionalidad correspondiente se oculta o se desactiva.

| Variable | Uso |
|---|---|
| `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | Django |
| `DATABASE_URL`, `REDIS_URL` | Base de datos (PostGIS) y capa de canales. Ya los define `docker-compose.yml`. |
| `GOOGLE_MAPS_API_KEY`, `GOOGLE_GEOCODING_API_KEY` | Mapas, autocompletado y geocodificación |
| `PAYPAL_MODE`, `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET` | Pagos con PayPal (Orders v2) |
| `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET`, `TWITTER_API_KEY`, `TWITTER_API_SECRET` | Login social |
| `TINIFY_API_KEY` | Compresión de imágenes con Tinify (sin key se usa Pillow) |
| `EMAIL_*` | SMTP. Sin host, los correos se imprimen en consola. |

## Desarrollo

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py makemigrations --check --dry-run
docker compose logs -f web
```

### Dependencias

Las dependencias directas están en `requirements.in`, y `requirements.txt` es la versión
congelada. Para regenerarla:

```bash
{ echo "# Generado desde requirements.in con Python 3.12 (ver README.md)."; \
  echo "# Dependencias directas: requirements.in"; \
  docker run --rm -v "$PWD":/w -w /w python:3.12-slim-trixie sh -c \
    "pip install -q --root-user-action=ignore -r requirements.in >/dev/null && pip freeze"; \
} > requirements.txt
docker compose build web
```

## Estructura

| Ruta | Contenido |
|---|---|
| `config/` | Settings, URLs y ASGI (HTTP + WebSocket) |
| `apps/realty` | Propiedades, categorías y formularios dinámicos por especificación |
| `apps/messenger` | Chat (WebSocket) y conversaciones |
| `apps/payments` | Pagos bancarios y con PayPal |
| `apps/auctions` | Subastas |
| `apps/authentication` | Registro, perfiles y login social |
| `apps/comments`, `apps/logs`, `apps/multimedia`, `apps/project` | Comentarios, "me gusta", imágenes y contenido del sitio |
| `hydra/` | Librería interna de template tags para formularios |
| `api/` | API REST usada por el explorador del mapa |
