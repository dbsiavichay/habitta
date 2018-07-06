from django.db import models

class Profile(models.Model):
	class Meta:
		verbose_name = 'perfil'
		verbose_name_plural = 'perfiles'

	phone = models.CharField(max_length=16, blank=True, null=True, verbose_name='número de celular')
	website = models.URLField(blank=True, null=True, verbose_name='sitio web')
	image = models.ImageField(upload_to='users/profiles/', blank=True, null=True, verbose_name='foto de perfil')
	user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
