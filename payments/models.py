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

class Deposit(models.Model):
	STATUS_CHOICES = (
		(1, 'Ingresado'), (2, 'En proceso'), (3, 'Confirmado')
	)

	bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='banco')
	amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='valor')
	date = models.DateTimeField(verbose_name='fecha')
	voucher = models.CharField(max_length=64, verbose_name='número de comprobante')
	object_id = models.IntegerField()
	content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
	status = models.PositiveSmallIntegerField(default=1, choices=STATUS_CHOICES, verbose_name='estado')
	user = models.ForeignKey('auth.User', on_delete=models.CASCADE)