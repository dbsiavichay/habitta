# Habitta

Portal de clasificados (inmuebles, servicios y empleos) con mapa, chat en tiempo real,
subastas y pagos (transferencia bancaria y PayPal).

**Stack:** Django 5.2 · Python 3.12 · Django Channels 4 (daphne) · PostgreSQL 17 + PostGIS 3.5 ·
Redis 7 · Django REST Framework · Tailwind CSS 4 + daisyUI 5 · django-cotton · Alpine.js · HTMX.

## Levantar con Docker

```bash
cp .env.example .env.docker      # ajusta los valores (ver abajo)
docker compose up -d --build
```

La app queda en <http://localhost:8000>.

> Si venías del proyecto con el nombre anterior, el volumen de la base cambió a `habitta_pgdata` y se
> restaura solo desde el dump. El volumen viejo no se borra; cuando ya no lo necesites:
> `docker volume rm larbit_pgdata`.

- `docker-compose.override.yml` se aplica automáticamente y activa el modo desarrollo:
  `DEBUG=True`, `runserver` con recarga en caliente y el código montado como volumen.
- El contenedor `web` espera a la base de datos y ejecuta `migrate` al arrancar.
- Para crear un administrador:

  ```bash
  docker compose exec web python manage.py createsuperuser
  ```

### Datos iniciales (dump)

Si existe `backups/seed-2020-04-27.pgsql`, se restaura automáticamente **la primera vez**
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
docker compose exec web python manage.py test apps.project.tests   # pruebas de humo del frontend
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

## Frontend

Sin Node: todo se instala con pip y se compila con el binario standalone de Tailwind.

| Pieza | Para qué |
|---|---|
| [Tailwind CSS 4](https://tailwindcss.com) + [daisyUI 5](https://daisyui.com) vía `django-tailwind-cli` | Estilos y componentes base. Fuente: `assets/tailwind/source.css` → `static/css/habitta.css` (generado, fuera de git) |
| [django-cotton](https://django-cotton.com) | Componentes con sintaxis HTML en `templates/cotton/` (`<c-button>`, `<c-property.card>`…) |
| [Alpine.js](https://alpinejs.dev) | Interactividad declarativa (`static/js/habitta/*.js`) |
| [HTMX](https://htmx.org) + `django-htmx` | Parciales sin recargar (p. ej. "Guardar" en favoritos) |
| [Lucide](https://lucide.dev/icons) (`{% lucide %}` / `<c-icon name="…">`) | Íconos SVG |
| PhotoSwipe, @googlemaps/markerclusterer | Galería y agrupación de pines (vendorizados en `static/vendor/`) |

- **Desarrollo:** `docker compose up -d` levanta también el servicio `tailwind`, que recompila el CSS al
  guardar plantillas. La primera vez descarga el CLI (~110 MB) en `.django_tailwind_cli/`.
  Si creas una carpeta nueva de plantillas, reinicia el watcher: `docker compose restart tailwind`.
- **Producción:** el `Dockerfile` ejecuta `manage.py tailwind build` antes de `collectstatic`.
- **Marca:** colores, radios y tipografía son tokens del tema `habitta` / `habitta-dark` en
  `assets/tailwind/source.css`; en las plantillas se usan clases semánticas (`bg-primary`,
  `text-secondary`…), nunca colores sueltos. Logo y favicons en `static/brand/`.
- **Nombre y contacto:** `SITE_NAME`, `SITE_URL`, `CONTACT_*` y `SOCIAL_*` (ver `.env.example`).
- **Diseño anterior:** las páginas de cuenta y del panel todavía usan la plantilla CityBook
  (`templates/base/`); las públicas usan `templates/layouts/base.html`. Los formularios nuevos usan
  `{% with hydra_theme="v2" %}` para renderizarse con `templates/hydra/v2/`.

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
| `templates/layouts/`, `templates/cotton/` | Layout base y componentes del diseño Habitta |
| `assets/tailwind/` | Hoja fuente de Tailwind con los temas de la marca |
| `api/` | API REST usada por el explorador del mapa |
