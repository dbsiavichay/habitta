from django.db import models

# Create your models here.

class Settings(models.Model):
	class Meta:
		verbose_name = 'Configuración'
		verbose_name_plural = 'Configuración'

	title = models.CharField(max_length=128, verbose_name='título principal')
	subtitle = models.CharField(max_length=128, verbose_name='subtitulo')

	def __str__(self):
		return self.title

class Term(models.Model):
	class Meta:
		verbose_name = 'Término'
		ordering = ['order',]

	title = models.CharField(max_length=64, verbose_name='título')
	description = models.TextField(verbose_name='descripción')
	order = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='orden')

	def __str__(self):
		return self.title

class Help(models.Model):
	class Meta:
		verbose_name = 'Ayuda'
		ordering = ['sequence']

	title = models.CharField(max_length=64, verbose_name='título')
	description = models.TextField(verbose_name='descripción')
	pub_date = models.DateTimeField(auto_now_add=True, verbose_name='fecha de publicación')
	sequence = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='secuencia')
	user = models.ForeignKey('auth.User', verbose_name='usuario', on_delete=models.CASCADE)

	def __str__(self):
		return self.title