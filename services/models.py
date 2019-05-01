from django.contrib.gis.db import models
from multimedia.mixins import ImageMixin

class Activity(models.Model):
	class Meta:
		verbose_name = 'actividad'
		verbose_name_plural = 'actividades'
		ordering = ['order',]

	name = models.CharField(max_length=64, verbose_name='nombre')
	order = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='orden')

	def __str__(self):
		return self.name


class Service(ImageMixin, models.Model):
	business_name = models.CharField(max_length=32, verbose_name='nombre de negocio')
	description = models.TextField(verbose_name='descripción')	
	address = models.CharField(max_length=64, verbose_name='dirección')
	geopoint = models.PointField(blank=True, null=True)
	business_phone = models.CharField(max_length=10, blank=True, null=True, verbose_name='telefono de negocio')
	date = models.DateTimeField(auto_now_add=True)
	activity = models.ForeignKey(Activity, verbose_name='actividad', on_delete=models.CASCADE)
	user = models.ForeignKey('auth.User', on_delete=models.CASCADE)

	def __str__(self):
		return '%s, %s' % (self.activity, self.user.username)
		
	class Meta:
		verbose_name = 'servicio'
		ordering = ['activity__name']
