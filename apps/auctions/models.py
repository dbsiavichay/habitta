from django.utils import timezone
from django.db import models
 
class Auction(models.Model):
    OPEN, CLOSED, CANCELED = (1,2,3)
    STAGE_CHOICES = ((OPEN, 'Abierto'),(CLOSED, 'Finalizado'),(CANCELED, 'Cancelado'))

    property = models.ForeignKey('realty.Property', on_delete=models.CASCADE, verbose_name='tus publicaciones disponibles')
    start_date = models.DateTimeField()
    ending_date = models.DateTimeField()
    base_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='monto base')   
    stage = models.PositiveSmallIntegerField(default=OPEN, choices=STAGE_CHOICES)

    def __str__(self):
        return 'Subasta de %s' % str(self.property)

    def _check_stage(self): 
        if self.stage == self.OPEN and self.ending_date <= timezone.now():
            self.stage = self.CLOSED
            self.save()

    def get_payment_amount(self):       
        return float(self.base_amount)*0.10

    #Usado para pagos
    def get_absolute_url(self):
        return self.property.get_absolute_url()

    class Meta:
        verbose_name = 'subasta'
        ordering = ('-start_date',)

class Offer(models.Model):
    class Meta:
        verbose_name = 'oferta'

    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE)