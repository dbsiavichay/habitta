from django import forms
from .models import Message

class MessageForm(forms.ModelForm):
	receiver = forms.IntegerField(widget=forms.HiddenInput())
	success_url = forms.CharField(widget=forms.HiddenInput())

	class Meta:
		model = Message
		exclude = ('create_date','sender', 'conversation')		

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['content'].widget.attrs.update({'placeholder':'Tú mensaje'})
	