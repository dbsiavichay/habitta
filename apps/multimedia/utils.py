import base64
import binascii
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image as PilImage, UnidentifiedImageError

# Formatos aceptados para imágenes subidas en base64 -> extensión del archivo
ALLOWED_IMAGE_FORMATS = {'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp'}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def base64_to_image(base64image):
	"""Decodifica un data-URI base64 y valida que sea una imagen real.

	La extensión se toma del contenido (detectado por Pillow), nunca del MIME
	declarado por el cliente: así no se puede subir SVG/HTML como "imagen".
	Devuelve ``(ContentFile, extension)`` o lanza ``ValidationError``.
	"""
	try:
		_, imgstr = base64image.split(';base64,', 1)
		raw = base64.b64decode(imgstr, validate=True)
	except (ValueError, binascii.Error):
		raise ValidationError('La imagen no tiene un formato válido.')

	if len(raw) > MAX_IMAGE_BYTES:
		raise ValidationError('La imagen supera el tamaño máximo de 5 MB.')

	try:
		with PilImage.open(BytesIO(raw)) as img:
			img.verify()
			image_format = img.format
	except (UnidentifiedImageError, OSError, SyntaxError):
		raise ValidationError('El archivo no es una imagen válida.')

	if image_format not in ALLOWED_IMAGE_FORMATS:
		raise ValidationError('Formato no permitido. Usa JPG, PNG o WEBP.')

	return ContentFile(raw), ALLOWED_IMAGE_FORMATS[image_format]


def compress_image(path):
	"""Comprime una imagen en disco, en el mismo archivo.

	Usa Tinify si hay TINIFY_API_KEY; si no (o si Tinify falla) usa Pillow.
	Nunca lanza excepciones: una compresión fallida no debe romper la petición.
	"""
	import logging

	from django.conf import settings

	logger = logging.getLogger(__name__)

	if settings.TINIFY_API_KEY:
		try:
			import tinify

			tinify.key = settings.TINIFY_API_KEY
			tinify.from_file(path).to_file(path)
			return
		except Exception:  # noqa: BLE001 - cualquier error de red/cuota cae a Pillow
			logger.warning('Tinify no disponible, se comprime con Pillow', exc_info=True)

	try:
		with PilImage.open(path) as img:
			img.load()
			image_format = img.format
			options = {'optimize': True}
			if image_format in ('JPEG', 'WEBP'):
				options['quality'] = 85
			img.save(path, image_format, **options)
	except (OSError, ValueError):
		logger.warning('No se pudo comprimir %s', path, exc_info=True)


def delete_image_file_on_commit(storage, name):
	"""Borra el archivo de una imagen cuando la transacción se confirma.

	Si la transacción se revierte el archivo sigue ahí (la fila también), y si otra fila de Image
	todavía apunta al mismo archivo, no se borra.
	"""
	from django.db import transaction

	from .models import Image

	def delete():
		if not Image.objects.filter(img=name).exists():
			storage.delete(name)

	if name:
		transaction.on_commit(delete)
