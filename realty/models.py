from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.contrib.gis.db import models
from django.urls import reverse_lazy
from multimedia.mixins import ImageMixin

from .utils import get_category_icons, get_larbit_icons

from fontawesome.fields import IconField

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

class Service(models.Model):
	ICON_CHOICES = get_larbit_icons()

	name = models.CharField(max_length=32, verbose_name='nombre')
	icon = models.CharField(max_length=32, blank=True, null=True, choices=ICON_CHOICES, verbose_name='ícono')

	def __str__(self):
		return self.name

	class Meta:
		verbose_name = 'servicio'
		ordering = ('name',)

class Specification(models.Model):
	ICON_CHOICES = get_larbit_icons()

	FIELD_CHOICES = (		
		('CharField', 'Texto'),('IntegerField', 'Número Entero'),
		('ChoiceField', 'Selector'), ('ChoiceField:RadioSelect', 'RadioMultiple'), 
		('FileField', 'Archivo'),
	)	
	
	name = models.CharField(max_length=128, verbose_name='nombre')
	internal_name = models.CharField(max_length=128, verbose_name='nombre interno')
	field_type = models.CharField(max_length=64, choices=FIELD_CHOICES, verbose_name='tipo de campo')
	attributes = models.CharField(max_length=128, blank=True, null=True, verbose_name='atributos')
	choices = models.CharField(max_length=256, blank=True, null=True, verbose_name='elecciones')	
	icon = models.CharField(max_length=32, blank=True, null=True, choices=ICON_CHOICES, verbose_name='ícono')
	is_required = models.BooleanField(default=False, verbose_name='requerido?')
	order = models.PositiveSmallIntegerField(default=1, verbose_name='orden')	

	def __str__(self):
		return self.name
		
	class Meta:
		verbose_name = 'especificación'
		verbose_name_plural = 'especificaciones'
		ordering = ['name',]

class Group(models.Model):
	name = models.CharField(max_length=64, verbose_name='nombre')
	internal_name = models.CharField(max_length=64, verbose_name='nombre de uso interno')	
	specifications = models.ManyToManyField(Specification, verbose_name='especifaciones para este grupo')

	class Meta:
		verbose_name = 'grupo'

class Category(models.Model):	
	class Meta:
		verbose_name = 'categoría'
		ordering = ('order',)

	ICON_CHOICES = get_category_icons()

	REAL_STATE, SERVICE = (1, 2)
	KIND_CHOICES = (
		(REAL_STATE, 'Inmobiliario'), (SERVICE, 'Servicio')
	)
	
	kind = models.PositiveSmallIntegerField(choices=KIND_CHOICES, verbose_name='tipo')
	name = models.CharField(max_length=64, verbose_name='nombre')
	singular_name = models.CharField(max_length=64, verbose_name='nombre singular')	
	enabled = models.BooleanField(default=True, verbose_name='habilitado?')
	icon = models.CharField(max_length=32, blank=True, null=True, choices=ICON_CHOICES, verbose_name='icono')
	order = models.PositiveSmallIntegerField(verbose_name='orden')	
	require_location = models.BooleanField(default=True, verbose_name='requiere ubicación?')
	purposes = models.ManyToManyField(Purpose, blank=True, verbose_name='propósitos')
	services = models.ManyToManyField(Service, blank=True, verbose_name='servicios')
	specifications = models.ManyToManyField(Specification, blank=True, verbose_name='especificaciones')
	groups = models.ManyToManyField(Group, through='GroupCategory', blank=True, verbose_name='grupos de especificaciones')

	def __str__(self):
		return self.name

class GroupCategory(models.Model):
	group = models.ForeignKey(Group, on_delete=models.CASCADE, verbose_name='grupo')
	category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name='categoría')
	sequence = models.PositiveSmallIntegerField(verbose_name='secuencia')

	class Meta:
		verbose_name = 'grupo de categoría'
		verbose_name_plural = 'grupos de categoría'

class Property(ImageMixin, models.Model):
	class Meta:
		verbose_name = 'propiedad'
		verbose_name_plural = 'propiedades'
		ordering = ['-pub_date',]

	DRAFT, PUBLISHED, COMPLETE = (1, 2, 3)

	STATUS_CHOICES = (
		(DRAFT, 'Borrador'), (PUBLISHED, 'Publicado'), (COMPLETE, 'Completado'),
	)

	title = models.CharField(max_length=32, verbose_name='título, nombre, negocio, etc.')
	price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='precio')
	negotiable = models.BooleanField(default=False, verbose_name='negociable?')
	description = models.TextField(blank=True, null=True, verbose_name='descripción')
	address = models.CharField(max_length=64, blank=True, null=True, verbose_name='dirección')
	geopoint = models.PointField(blank=True, null=True)	
	status = models.PositiveSmallIntegerField(default=DRAFT)
	details = JSONField(blank=True, null=True, verbose_name='detalles')	
	pub_date = models.DateTimeField(auto_now_add=True, verbose_name='fecha de publicación')	
	category = models.ForeignKey(Category, verbose_name='categoría', on_delete=models.CASCADE)	
	user = models.ForeignKey('auth.User', verbose_name='propietario', on_delete=models.CASCADE)

	def __str__(self):
		return self.description

	def get_purpose(self):
		try:
			pk = self.details['purpose']
			purpose = Purpose.objects.get(pk=pk)
			return purpose		
		except:
			return {'activity': 'No definido'}

	def get_specifications(self):
		specifications = []

		for spc in self.category.specifications.all():
			key = str(spc.id)
			if key in self.details['specifications']:
				specifications.append({
					'key': spc.name,
					'value': self.details['specifications'][key],
					'icon': spc.icon,
					'require_payment': True if 'FileField' in spc.field_type else False
				})
		return specifications

	def get_path_files(self):
		files = []

		for spc in self.category.specifications.all():
			key = str(spc.id)
			if 'FileField' in spc.field_type and key in self.details['specifications']:
				files.append(self.details['specifications'][key])
		return files

	def get_services(self):
		services =	Service.objects.filter(pk__in=self.details['services'])		
		return services

	def get_absolute_url(self):		
		return reverse_lazy('detail_property', args=[str(self.id)])





#Eliminar despues de subir a producción
class PropertyImage(models.Model):
	class Meta:
		verbose_name = 'imagen'
		verbose_name_plural = 'imagenes'

	img = models.ImageField(upload_to='properties/images/', verbose_name='imagen')
	is_cover = models.BooleanField(default=False, verbose_name='de portada?')
	property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')