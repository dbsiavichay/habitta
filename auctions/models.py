from django.db import models

class Auction(models.Model):
	class Meta:
		verbose_name = 'subasta'

	start_date = models.DateTimeField()
	ending_date = models.DateTimeField()
	base_amount = models.DecimalField(max_digits=10, decimal_places=2)
	property = models.ForeignKey('realty.Property', on_delete=models.CASCADE)

class Offer(models.Model):
	class Meta:
		verbose_name = 'oferta'

	user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
	date = models.DateTimeField(auto_now_add=True)
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	auction = models.ForeignKey(Auction, on_delete=models.CASCADE)