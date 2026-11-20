from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from .managers import ImageManager

class Image(models.Model):
	class Meta:
		verbose_name = 'imagen'
		verbose_name_plural = 'imágenes'

	code = models.CharField(max_length=16, blank=True, null=True)
	img = models.ImageField(upload_to='images', verbose_name='imagen')
	is_cover = models.BooleanField(default=False, verbose_name='de portada?')
	object_id = models.IntegerField()
	content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
	# Sin columna propia: permite que los modelos dueños declaren GenericRelation (borrado en cascada)
	content_object = GenericForeignKey('content_type', 'object_id')
	objects = ImageManager()

	def set_object(self, obj):
		self.object_id = obj.id
		self.content_type = ContentType.objects.get_for_model(obj)

	def get_object(self):
		return self.content_type.get_object_for_this_type(pk=self.object_id)

