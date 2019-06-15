from django.db import models

class Conversation(models.Model):
	owner = models.ForeignKey('auth.User', on_delete=models.PROTECT, related_name='outbox')	
	member = models.ForeignKey('auth.User', on_delete=models.PROTECT, related_name='inbox')	
	create_date = models.DateTimeField(auto_now_add=True)

	def last_message(self):
		return self.messages.last()

	class Meta:
		unique_together = ('owner', 'member')

class Message(models.Model):
	sender = models.ForeignKey('auth.User', on_delete=models.PROTECT)	
	content = models.TextField()	
	create_date = models.DateTimeField(auto_now_add=True)
	conversation = models.ForeignKey(Conversation, on_delete=models.PROTECT, related_name='messages')
