from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.contrib.gis.db import models
from django.urls import reverse_lazy
from .utils import get_category_icons

from fontawesome.fields import IconField

class Service(models.Model):
	class Meta:
		verbose_name = 'servicio'
		ordering = ('name',)
		
	name = models.CharField(max_length=32, verbose_name='nombre')
	icon = IconField(verbose_name='ícono')

	def __str__(self):
		return self.name

class Specification(models.Model):
	class Meta:
		verbose_name = 'especificación'
		verbose_name_plural = 'especificaciones'
		ordering = ['order',]

	WIDGET_CHOICES = (
		('TextInput', 'Texto'), ('NumberInput', 'Número'), 
		('Select', 'Selector'), ('RadioSelect', 'RadioMultiple'),
	)	
	
	name = models.CharField(max_length=128, verbose_name='nombre')
	internal_name = models.CharField(max_length=128, verbose_name='nombre interno')
	widget = models.CharField(max_length=64, choices=WIDGET_CHOICES)
	choices = models.CharField(max_length=256, blank=True, null=True, verbose_name='elecciones')	
	icon = IconField(verbose_name='ícono')
	is_required = models.BooleanField(default=False, verbose_name='requerido?')
	order = models.PositiveSmallIntegerField(default=1, verbose_name='orden')	

	def __str__(self):
		return self.name

class Category(models.Model):	
	class Meta:
		verbose_name = 'categoría'
		ordering = ('order',)

	ICON_CHOICES = get_category_icons()

	name = models.CharField(max_length=32, verbose_name='nombre')
	icon = models.CharField(max_length=32, blank=True, null=True, choices=ICON_CHOICES, verbose_name='icono')
	order = models.PositiveSmallIntegerField(verbose_name='orden')	
	services = models.ManyToManyField(Service, blank=True, verbose_name='servicios')
	specifications = models.ManyToManyField(Specification, blank=True, verbose_name='especificaciones')

	def __str__(self):
		return self.name

#Lo que se pretende hacer con la propiedad ej: vender, rentar
class Purpose(models.Model):
	class Meta:
		verbose_name = 'propósito'
		ordering = ['order',]

	for_owner = models.CharField(max_length=32, verbose_name='para el propietario')	
	for_user = models.CharField(max_length=32, verbose_name='para el usuario')		
	activity = models.CharField(max_length=32, verbose_name='actividad')
	participle = models.CharField(max_length=32, verbose_name='participio')
	order = models.PositiveSmallIntegerField(default=1, verbose_name='orden')

	def __str__(self):
		return self.for_owner

class Property(models.Model):
	class Meta:
		verbose_name = 'propiedad'
		verbose_name_plural = 'propiedades'

	DRAFT, PUBLISHED, COMPLETE = (1, 2, 3)

	STATUS_CHOICES = (
		(DRAFT, 'Borrador'), (PUBLISHED, 'Publicado'), (COMPLETE, 'Completado'),
	)
	
	price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='precio')
	description = models.TextField(blank=True, null=True, verbose_name='descripción')
	address = models.CharField(max_length=64, verbose_name='dirección')
	geopoint = models.PointField()	
	status = models.PositiveSmallIntegerField(default=DRAFT)
	details = JSONField(blank=True, null=True, verbose_name='detalles')
	pub_date = models.DateTimeField(auto_now_add=True)
	purpose	 = models.ForeignKey(Purpose, verbose_name='¿Que desea hacer?', on_delete=models.CASCADE)
	category = models.ForeignKey(Category, verbose_name='categoría', on_delete=models.CASCADE)	
	user = models.ForeignKey('auth.User', verbose_name='propietario', on_delete=models.CASCADE)

	def __str__(self):
		return self.description

	def get_specifications(self):
		specifications = []

		for spc in self.category.specifications.all():
			key = str(spc.id)
			if key in self.details['specifications']:
				specifications.append({
					'key': spc.name,
					'value': self.details['specifications'][key],
					'icon': spc.icon
				})
		return specifications

	def get_services(self):
		services =	Service.objects.filter(pk__in=self.details['services'])		
		return services

	def get_cover_instance(self):
		instances = self.images.filter(is_cover=True)

		if len(instances) > 0:
			return instances[0]		

	def get_cover(self):
		instance = self.get_cover_instance()

		if instance and instance.img:
			return instance.img.url

		return settings.STATIC_URL + 'images/bg/1.jpg'

	def get_gallery(self):
		instances = self.images.filter(is_cover=False)
		images = [i.img for i in instances if i.img]
		return images

	def get_absolute_url(self):		
		return reverse_lazy('detail_property', args=[str(self.id)])

class PropertyImage(models.Model):
	class Meta:
		verbose_name = 'imagen'
		verbose_name_plural = 'imagenes'

	img = models.ImageField(upload_to='properties/images/', verbose_name='imagen')
	is_cover = models.BooleanField(default=False, verbose_name='de portada?')
	property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')