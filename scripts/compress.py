"""Recomprime las portadas de todas las propiedades.

Uso: docker compose exec web python manage.py shell < scripts/compress.py
Usa Tinify si hay TINIFY_API_KEY; si no, Pillow.
"""
import os

from apps.multimedia.utils import compress_image
from apps.realty.models import Property

for p in Property.objects.all():
	cover = p.get_cover_instance()
	if cover and cover.img and os.path.isfile(cover.img.path):
		path = cover.img.path
		before = os.path.getsize(path)
		compress_image(path)
		print(f'{path}: {before} -> {os.path.getsize(path)} bytes')
