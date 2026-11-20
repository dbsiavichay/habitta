import os
import re

from django.conf import settings
from django.db import DatabaseError


def _read_icon_names(path, prefix):
	"""Extrae los nombres de íconos (``.<prefix>-<nombre>:before``) de un CSS."""
	regex = re.compile(r'%s-(?P<icon>[\w_-]+):before' % prefix)
	try:
		with open(path, 'r', encoding='utf-8') as file:
			return sorted(set(regex.findall(file.read())))
	except OSError:
		return []


def get_category_icons():
	icons = _read_icon_names(os.path.join(settings.BASE_DIR, 'static/plugins/fontcategories/fontcategories.css'), 'fc')
	return [(icon, icon.capitalize()) for icon in icons]


def get_spec_icons():
	"""Íconos de especificaciones (clases ``lb-*``) de la fuente activa subida desde el admin.

	Son las ``choices`` de ``Specification.icon``: Django las evalúa también en el system check,
	así que con la BD vacía o sin migrar devuelve una lista vacía en vez de fallar.
	"""
	from apps.project.utils import get_active_icons

	try:
		icons = get_active_icons()
	except DatabaseError:
		return []
	if not icons or not icons.css:
		return []
	try:
		path = icons.css.path
	except (NotImplementedError, ValueError):
		return []
	return [(icon, ' '.join(icon.capitalize().split('-'))) for icon in _read_icon_names(path, 'lb')]


def attachment_paths(details):
	"""Rutas de los adjuntos (planos, PDFs…) guardados en ``details['specifications']``.

	Los guarda ``GroupDetailsForm`` como rutas absolutas dentro de ``MEDIA_ROOT/files/``; sólo se
	devuelven las que de verdad están ahí (el resto de valores son textos o números).
	"""
	root = os.path.join(os.path.realpath(settings.MEDIA_ROOT), 'files') + os.sep
	values = ((details or {}).get('specifications') or {}).values()
	return [value for value in values if isinstance(value, str) and os.path.realpath(value).startswith(root)]


def delete_attachments_on_commit(paths):
	"""Borra los adjuntos cuando la transacción se confirma (si se revierte, siguen ahí)."""
	from django.db import transaction

	def delete():
		for path in paths:
			try:
				os.remove(path)
			except OSError:
				pass

	if paths:
		transaction.on_commit(delete)


def property_photos(obj):
	"""Portada + galería de un anuncio con sus dimensiones (las necesita el visor PhotoSwipe).

	Lo usan el detalle del anuncio y el paso "Fotos" del asistente de publicación.
	"""
	from django.urls import reverse

	photos = []
	cover = obj.get_cover_instance()
	images = ([cover] if cover and cover.img else []) + list(obj.get_gallery())
	seen = set()
	for image in images:
		# Las imágenes generadas para el PDF (QR, mapa estático, miniatura) no son fotos del anuncio
		if image.pk in seen or image.code in ('qrcode', 'map', 'thumbnail'):
			continue
		seen.add(image.pk)
		try:
			width, height = image.img.width, image.img.height
		except (OSError, ValueError):
			# La imagen no existe en el almacenamiento: no se muestra
			continue
		photos.append({
			'id': image.pk,
			'url': image.img.url,
			'width': width,
			'height': height,
			'is_cover': image.is_cover,
			'delete_url': reverse('delete_image', args=[image.pk]),
		})
	return photos
