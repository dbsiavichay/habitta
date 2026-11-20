# syntax=docker/dockerfile:1

# ---------- Etapa 1: dependencias de Python ----------
FROM python:3.12-slim-trixie AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt


# ---------- Etapa 2: imagen de ejecución ----------
FROM python:3.12-slim-trixie AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings

# Librerías nativas que necesita GeoDjango (GDAL, GEOS, PROJ)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gdal-bin libgdal36 libgeos-c1t64 libproj25 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app . .

# Compila el CSS (Tailwind + daisyUI) y recopila los estáticos: no necesitan base de datos ni secretos reales.
# El binario standalone de Tailwind (~110 MB) sólo hace falta aquí: se descarga en /tmp y se borra en la misma capa.
RUN TAILWIND_CLI_PATH=/tmp/tailwind SECRET_KEY=build-only-key DEBUG=False python manage.py tailwind build \
    && rm -rf /tmp/tailwind /tmp/.django-tailwind-cli \
    && SECRET_KEY=build-only-key DEBUG=False python manage.py collectstatic --noinput \
    && mkdir -p /app/media \
    && chown -R app:app /app/staticfiles /app/media

USER app

# Commit con el que se construyó (CI pasa --build-arg GIT_SHA); lo informa /healthz.
# Va al final para no invalidar la caché de las capas anteriores en cada commit.
ARG GIT_SHA=dev
ENV APP_VERSION=$GIT_SHA

EXPOSE 8000

# /healthz responde 200 si Django y la base de datos están arriba. Host: localhost porque el chequeo
# no pasa por el proxy (ALLOWED_HOSTS lo incluye); start-period cubre la espera de la BD y migrate.
HEALTHCHECK --interval=15s --timeout=5s --start-period=90s --retries=3 \
    CMD ["python", "-c", "import urllib.request as u; u.urlopen(u.Request('http://127.0.0.1:8000/healthz', headers={'Host': 'localhost'}), timeout=4)"]

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
