from django.db import models
from decimal import Decimal

class Bank(models.Model):
	ACCOUNT_TYPE_CHOICES = (
		(1, 'Cuenta Corriente'), (2, 'Cuenta de Ahorros')
	)

	name = models.CharField(max_length=64, verbose_name='nombre')
	account_number = models.CharField(max_length=128, verbose_name='número de cuenta')
	account_type = models.PositiveSmallIntegerField(choices=ACCOUNT_TYPE_CHOICES, verbose_name='tipo de cuenta')
	recipient_name = models.CharField(max_length=128, verbose_name='nombre del beneficiario')
	recipient_charter = models.CharField(max_length=16, verbose_name='identificación del beneficiario')

	def get_account_type(self):
		return dict(self.ACCOUNT_TYPE_CHOICES).get(self.account_type)

	def __str__(self):
		return '%s, #%s, %s' % (self.name, self.account_number, self.get_account_type())

	class Meta:
		verbose_name = 'banco'

class Payment(models.Model):
	STATUS_CHOICES = (
		(1, 'Registro'), (2, 'Confirmado'), (3, 'Rechazado')
	)
	amount = models.DecimalField(max_digits=10, decimal_places=2, default = Decimal('0.00'), verbose_name='monto')
	user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
	object_id = models.IntegerField()
	content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
	status = models.PositiveSmallIntegerField(default=1, choices=STATUS_CHOICES)
	date = models.DateTimeField(auto_now_add=True)

	def get_object(self):
		return self.content_type.get_object_for_this_type(pk=self.object_id)

	def get_status(self):
		return dict(self.STATUS_CHOICES).get(self.status)

class BankPayment(Payment):
	bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='banco')
	voucher = models.FileField(upload_to='payments/bankvouchers', verbose_name='comprobante')

	class Meta:
		verbose_name = 'pago bancario'
		verbose_name_plural = 'pagos bancarios'

class PaypalPayment(models.Model):
	# Identificador de paypal para este pago
	payment_id = models.CharField(max_length=64)
	# Id unico asignado por paypal a cada usuario, no cambia aunque la dirección de email lo haga.
	payer_id = models.CharField(max_length=128, blank=True)
	# Dirección de email del cliente proporcionada por paypal.
	payer_email = models.EmailField(blank=True)
	# Guardamos una copia del precio, porque puede variar en el tiempo
	amount = models.DecimalField(max_digits=10, decimal_places=2, default = Decimal('0.00'))
	date = models.DateTimeField(auto_now_add=True)
	is_paid = models.BooleanField(default=False)
	user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
	property = models.ForeignKey('realty.Property', on_delete=models.CASCADE)

	class Meta:
		unique_together = ('user', 'property')
		verbose_name = 'pago paypal'
		verbose_name_plural = 'pagos paypal'