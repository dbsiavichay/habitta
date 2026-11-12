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

# collectstatic no necesita base de datos ni secretos reales
RUN SECRET_KEY=build-only-key DEBUG=False python manage.py collectstatic --noinput \
    && mkdir -p /app/media \
    && chown -R app:app /app/staticfiles /app/media

USER app

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
