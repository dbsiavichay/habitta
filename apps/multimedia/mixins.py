from django.conf import settings
from django.core.files.base import ContentFile
from io import BytesIO
import uuid

from .models import Image
from .utils import delete_image_file_on_commit


def _png_file(img):
	"""Serializa una imagen (Pillow o qrcode) a PNG: devuelve (nombre, ContentFile)."""
	buff = BytesIO()
	img.save(buff, 'PNG')
	return '%s.png' % uuid.uuid4(), ContentFile(buff.getvalue())

class ImageMixin(object):
	def get_last_image_by_code(self, code):
		try:
			instance = Image.objects.get_images_by_code(self, code).last()
		except:
			return None
		return instance

	def get_cover_instance(self):
		return Image.objects.get_cover(self)

	def get_cover(self):
		instance = self.get_cover_instance()

		if instance and instance.img:
			return instance.img.url

		return settings.STATIC_URL + 'brand/placeholder.svg'

	def get_cover_path(self):
		"""Ruta del archivo de la portada, o None si no tiene."""
		instance = self.get_cover_instance()

		if instance and instance.img:
			return instance.img.path

		return None

	def get_gallery(self):
		instances = Image.objects.get_gallery(self)
		images = [i for i in instances if i.img]
		return images

	def add_image(self, img, code=''):
		image = Image(code=code)
		image.set_object(self)

		image.img.save(*_png_file(img))

		image.save()
		return image

	def update_image(self, img, code):
		"""Reemplaza la imagen `code` (miniatura, mapa…) y borra el archivo anterior."""
		image = self.get_last_image_by_code(code)
		if not image:
			return self.add_image(img, code)

		old_name = image.img.name
		image.img.save(*_png_file(img))
		if old_name and old_name != image.img.name:
			delete_image_file_on_commit(image.img.storage, old_name)
		return image
