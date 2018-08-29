from django.db import models

class Log(models.Model):
	class Meta:
		unique_together = ('type', 'property', 'user')

	VIEW, LIKE = (1, 2,)

	TYPE_CHOICES = (
		(VIEW, 'Vista'), (LIKE, 'Me gusta'),
	)

	type = models.PositiveSmallIntegerField(choices=TYPE_CHOICES)
	date = models.DateTimeField(auto_now_add=True)
	property = models.ForeignKey('realty.Property', on_delete=models.CASCADE)
	user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
