from django.db import models
from .managers import ImageManager

class Image(models.Model):
	class Meta:
		verbose_name = 'imagen'
		verbose_name_plural = 'imagenes'

	img = models.ImageField(upload_to='images', verbose_name='imagen')
	is_cover = models.BooleanField(default=False, verbose_name='de portada?')
	object_id = models.IntegerField()
	content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
	objects = ImageManager()

	def get_object(self):
		return self.content_type.get_object_for_this_type(pk=self.object_id)
