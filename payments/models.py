from django.db import models

class Bank(models.Model):
	ACCOUNT_TYPE_CHOICES = (
		(1, 'Cuenta Corriente'), (2, 'Cuenta de Ahorros')
	)

	name = models.CharField(max_length=64, verbose_name='nombre')
	account_number = models.CharField(max_length=128, verbose_name='número de cuenta')
	account_type = models.PositiveSmallIntegerField(choices=ACCOUNT_TYPE_CHOICES, verbose_name='tipo de cuenta')
	recipient_name = models.CharField(max_length=128, verbose_name='nombre del beneficiario')
	recipient_charter = models.CharField(max_length=16, verbose_name='identificación del beneficiario')

	def __str__(self):
		return self.name

class Payment(models.Model):
	amount = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='valor')
	object_id = models.IntegerField()
	content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
	user = models.ForeignKey('auth.User', on_delete=models.CASCADE)