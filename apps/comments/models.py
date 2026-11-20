from django.db import models

class Comment(models.Model):
	class Meta:
		ordering = ['-date',]
		verbose_name = 'comentario'

	content = models.TextField(blank=True, null=True)	
	date = models.DateTimeField(auto_now_add=True)
	object_id = models.IntegerField()
	contenttype = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
	user = models.ForeignKey('auth.User', on_delete=models.CASCADE)

	def get_object_url(self):
		obj = self.contenttype.get_object_for_this_type(pk=self.object_id)
		return obj.get_absolute_url()

	def __str__(self):
		return self.content