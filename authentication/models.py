from django.conf import settings
from django.db import models
from django.urls import reverse
from multimedia.mixins import ImageMixin
from fontawesome.fields import IconField

class SocialNetwork(ImageMixin, models.Model):
	class Meta:
		verbose_name = 'red social'
		verbose_name_plural = 'redes sociales'

	name = models.CharField(max_length=32, verbose_name='nombre')
	icon = IconField(verbose_name='ícono')
	url = models.URLField()

	def __str__(self):
		return self.name

class Profile(models.Model):
	class Meta:
		verbose_name = 'perfil'
		verbose_name_plural = 'perfiles'

	phone = models.CharField(max_length=16, blank=True, null=True, verbose_name='número de celular')	
	image = models.ImageField(upload_to='users/profiles/', blank=True, null=True, verbose_name='foto de perfil')
	user = models.OneToOneField('auth.User', on_delete=models.CASCADE, verbose_name='usuario')
	social_networks = models.ManyToManyField(SocialNetwork,  through='SocialNetworkProfile', blank=True, verbose_name='redes sociales')

	def get_avatar(self):		
		if self.image:
			return self.image.url
		return settings.STATIC_URL + 'images/avatar/avatar-bg.png'

	def get_avatar_path(self):
		if self.image:
			return self.image.path
		return settings.BASE_DIR + '/static/images/avatar/avatar-bg.png'

	def get_absolute_url(self):
		return reverse('detail_profile', args=[self.user.username])

	def __str__(self):
		return self.user.get_full_name()

class SocialProfile(models.Model):
	class Meta:
		verbose_name = 'perfil social'
		verbose_name_plural = 'perfiles sociales'

	provider = models.CharField(max_length=16, verbose_name='proveedor')
	identifier = models.CharField(max_length=64, verbose_name='id usuario')
	user = models.ForeignKey('auth.User', on_delete=models.CASCADE, verbose_name='usuario')


class SocialNetworkProfile(models.Model):
	social_network = models.ForeignKey(SocialNetwork, on_delete=models.CASCADE)
	profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
	username = models.CharField(max_length=128)

	def get_url(self):
		return '{}{}'.format(self.social_network.url, self.username)
