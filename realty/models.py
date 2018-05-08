from django.db import models

class Category(models.Model):
	class Meta:
		verbose_name = 'categoría'

	name = models.CharField(max_length=32)

	def __str__(self):
		return self.name

class Service(models.Model):
	class Meta:
		verbose_name = 'servicio'
		
	name = models.CharField(max_length=32)

	def __str__(self):
		return self.name

class Property(models.Model):
	title = models.CharField(max_length=32, verbose_name='título')
	price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='precio')
	description = models.TextField( blank=True, null= True, verbose_name='descripción')
	#longitude = models.FloatField(blank=True, null=True, verbose_name='longitud')
	#latitude = models.FloatField(blank=True, null=True, verbose_name='latitud')
	#geolocation = models.PointField(blank=True, null=True)
	#video = models.FileField(upload_to='articles/videos/', blank=True, null=True)	
	#features = JSONField(verbose_name='caracteristicas')
	pub_date = models.DateTimeField(auto_now_add=True)	
	category = models.ForeignKey(Category, verbose_name='categoría', on_delete=models.CASCADE)	
	services = models.ManyToManyField(Service, blank=True,verbose_name='servicios')
	user = models.ForeignKey('auth.User', verbose_name='propietario', on_delete=models.CASCADE)

class PropertyImage(models.Model):
	image = models.ImageField(upload_to='properties/images/')
	property = models.ForeignKey(Property, on_delete=models.CASCADE)