from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from io import BytesIO
import uuid

from .models import Image

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

		return settings.STATIC_URL + 'images/bg/1.png'

	def get_cover_path(self):
		instance = self.get_cover_instance()

		if instance and instance.img:
			return instance.img.path

		return settings.BASE_DIR + '/static/images/bg/1.png'

	def get_gallery(self):
		instances = Image.objects.get_gallery(self)
		images = [i for i in instances if i.img]
		return images

	def add_image(self, img, code=''):
		image = Image(code=code)
		image.set_object(self)

		buff = BytesIO()
		img.save(buff, 'PNG')
		filename = '%s.png' % (str(uuid.uuid4()),)
		filebuffer = InMemoryUploadedFile(buff, None, filename, 'image/png', img.tell, None)
		image.img.save(filename, filebuffer)

		image.save()
		return image
