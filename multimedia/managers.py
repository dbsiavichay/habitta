from django.db import models
from django.contrib.contenttypes.models import ContentType

class ImageManager(models.Manager):
	def get_images(self, obj, is_cover):
		ct = ContentType.objects.get_for_model(obj)
		return self.filter(object_id=obj.id, content_type=ct, is_cover=is_cover)

	def get_gallery(self, obj):		
		return self.get_images(obj, False)

	def get_cover(self, obj):
		ct = ContentType.objects.get_for_model(obj)
		object_list = self.get_images(obj, True)
		return object_list[0] if object_list else None	
