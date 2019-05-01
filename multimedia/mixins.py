from django.conf import settings
from .models import Image

class ImageMixin(object):
	def get_cover_instance(self):
		return Image.objects.get_cover(self)

	def get_cover(self):
		instance = self.get_cover_instance()

		if instance and instance.img:
			return instance.img.url

		return settings.STATIC_URL + 'images/bg/1.png'

	def get_gallery(self):
		instances = Image.objects.get_gallery(self)
		images = [i for i in instances if i.img]
		return images