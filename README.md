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
| `SITE_NAME`, `SITE_TAGLINE`, `SITE_URL`, `LEGAL_NAME`, `CONTACT_*`, `SOCIAL_*` | Marca, URL pública (enlaces absolutos y QR del PDF), razón social de los términos y datos de contacto |
| `DATABASE_URL`, `REDIS_URL` | Base de datos (PostGIS) y capa de canales. Ya los define `docker-compose.yml`. |
| `GOOGLE_MAPS_API_KEY` | Mapas, autocompletado, geocodificación y mapa estático del PDF |
| `PAYPAL_MODE`, `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET` | Pagos con PayPal (Orders v2) |
| `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET`, `TWITTER_API_KEY`, `TWITTER_API_SECRET` | Login social |
| `TINIFY_API_KEY` | Compresión de imágenes con Tinify (sin key se usa Pillow) |
| `EMAIL_*` | SMTP. Sin host, los correos se imprimen en consola. |

## Desarrollo

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py makemigrations --check --dry-run
docker compose exec web python manage.py test apps.project.tests apps.authentication.tests \
    apps.realty.tests apps.messenger.tests apps.auctions.tests apps.payments.tests apps.multimedia.tests
docker compose logs -f web
```

### Mantenimiento de datos

Comandos para la base de datos y `media/` (córrelos siempre primero con `--dry-run`: los archivos
borrados no se recuperan, `media/` no está en git).

| Comando | Qué hace |
|---|---|
| `manage.py rebrand_content [--dry-run] [--legal-name …] [--domain …]` | Cambia la marca anterior (Larbit) en el título del sitio y en los términos (razón social → `LEGAL_NAME`, `www.larbit.com` → dominio de `SITE_URL`) y mueve la fuente de íconos de especificaciones a `media/spec_icons/`. No toca datos de usuarios. |
| `manage.py purge_orphan_images [--dry-run] [--files]` | Borra las filas de `Image` cuyo objeto ya no existe y sus archivos; con `--files`, también los archivos de `media/images/` que ninguna fila usa. |

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
| PhotoSwipe, @googlemaps/markerclusterer, Cropper.js | Galería, agrupación de pines y recorte de la portada (vendorizados en `static/vendor/`) |

- **Desarrollo:** `docker compose up -d` levanta también el servicio `tailwind`, que recompila el CSS al
  guardar plantillas. La primera vez descarga el CLI (~110 MB) en `.django_tailwind_cli/`.
  Si creas una carpeta nueva de plantillas, reinicia el watcher: `docker compose restart tailwind`.
- **Producción:** el `Dockerfile` ejecuta `manage.py tailwind build` antes de `collectstatic`.
- **Marca:** colores, radios y tipografía son tokens del tema `habitta` / `habitta-dark` en
  `assets/tailwind/source.css`; en las plantillas se usan clases semánticas (`bg-primary`,
  `text-secondary`…), nunca colores sueltos. Logo y favicons en `static/brand/`.
- **PDF del anuncio:** `apps/realty/report.py` lo dibuja con reportlab usando el logo de
  `static/brand/` y Plus Jakarta Sans (`assets/fonts/`, licencia OFL).
- **Nombre y contacto:** `SITE_NAME`, `SITE_URL`, `CONTACT_*` y `SOCIAL_*` (ver `.env.example`).
- **Layouts:** `templates/layouts/base.html` (páginas públicas), `auth.html` (login, registro y
  recuperación) y `app.html` (panel del usuario, con el menú definido en `apps/project/panel.py`).
  Los formularios se pintan con `{% include 'hydra/form.html' %}` o `{% render_field campo %}`
  (`{% load hydra %}`), que usa la plantilla del widget en `templates/hydra/forms/`.

## Admin

`/admin/` usa [django-unfold](https://unfoldadmin.com), que trae su propio CSS compilado (no pasa
por nuestro Tailwind).

- **Configuración:** `config/unfold.py` reúne la marca, los colores (escalas OKLCH sacadas de la
  paleta), el menú lateral por tareas y los callbacks. Cada ítem del menú se oculta si el usuario no
  tiene permiso de lectura sobre ese modelo.
- **Dashboard:** `templates/admin/index.html` + `apps/project/admin_dashboard.py`. Sólo usa
  componentes de Unfold y clases que ya existen en `unfold/static/unfold/css/styles.css`.
- **ModelAdmin:** heredan de `unfold.admin.ModelAdmin`/`TabularInline`. Si heredan del admin de
  Django, la pantalla queda sin estilos. Las piezas comunes están en `apps/project/admin_utils.py`:
  - `user_header`, `site_link`, `image_preview` y `short_date`.
  - `label_html`: `@display(label=…)` no se aplica a los campos de sólo lectura del detalle.
  - `ReadOnlyChangeFormMixin`: oculta "Guardar" en fichas sin campos editables.
  - `back_to_page`: respuesta de las acciones con diálogo.
- **Transferencias:** se confirman o rechazan con las acciones de Unfold (`actions_row`,
  `actions_detail` y en lote), que abren un diálogo. Cada cambio avisa al usuario por correo
  (`apps/payments/notifications.py`). Sólo se resuelven las que están "por confirmar".
- **Conversaciones:** son mensajes privados. Sólo las ven los superusuarios, en modo de sólo lectura.
- **Retoques:** `static/css/admin.css` (tipografía) y `static/js/admin.js` (fuente de los gráficos).
- **Traducciones:** Unfold no trae español, así que `locale/es/LC_MESSAGES/django.po` traduce sus
  cadenas. Después de editarlo hay que compilarlo y subir el `.mo` a git (en la Mac,
  `brew install gettext`):

  ```bash
  msgfmt --check -o locale/es/LC_MESSAGES/django.mo locale/es/LC_MESSAGES/django.po
  ```

  Al actualizar Unfold conviene revisar si tiene cadenas nuevas sin traducir.

## Estructura

| Ruta | Contenido |
|---|---|
| `config/` | Settings, URLs y ASGI (HTTP + WebSocket) |
| `apps/realty` | Propiedades, categorías y formularios dinámicos por especificación |
| `apps/messenger` | Chat (WebSocket) y conversaciones |
| `apps/payments` | Pagos bancarios y con PayPal |
| `apps/auctions` | Subastas |
| `apps/authentication` | Registro, perfiles y login social |
| `apps/logs`, `apps/multimedia`, `apps/project` | "Me gusta", imágenes y contenido del sitio |
| `apps/comments` | Comentarios antiguos: no se muestran en el sitio, sólo en el admin |
| `hydra/` | Librería interna de template tags para formularios |
| `templates/layouts/`, `templates/cotton/` | Layout base y componentes del diseño Habitta |
| `assets/tailwind/`, `assets/fonts/` | Hoja fuente de Tailwind con los temas de la marca y la fuente del PDF |
| `api/` | API REST usada por el explorador del mapa |
