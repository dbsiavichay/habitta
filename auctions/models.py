from django.db import models

class Auction(models.Model):
	OPEN, CLOSED, CANCELED = (1,2,3)
	STAGE_CHOICES = ((OPEN, 'Abierto'),(CLOSED, 'Finalizado'),(CANCELED, 'Cancelado'))

	property = models.ForeignKey('realty.Property', on_delete=models.CASCADE)
	start_date = models.DateTimeField()
	ending_date = models.DateTimeField()
	base_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='monto base')	
	stage = models.PositiveSmallIntegerField(default=OPEN, choices=STAGE_CHOICES)
	is_active = models.BooleanField(default=True)

	def timeuntil(self):
		now = timezone.now()
		if now < self.start_date:
			return 'La puja inicia en %s.' % timeuntil(self.start_date)
		elif now > self.ending_date:
			return 'La puja ha finalizado.'
		else:
			return 'La puja finaliza en %s.' % timeuntil(self.ending_date)

	class Meta:
		verbose_name = 'subasta'

class Offer(models.Model):
	class Meta:
		verbose_name = 'oferta'

	user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
	date = models.DateTimeField(auto_now_add=True)
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	auction = models.ForeignKey(Auction, on_delete=models.CASCADE)