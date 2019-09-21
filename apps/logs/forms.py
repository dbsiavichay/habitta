from django.forms import ModelForm
from django.forms.widgets import HiddenInput

from .models import Log

class LogForm(ModelForm):
	class Meta:
		model = Log
		fields = ('type', 'property')
		widgets = {
			'type': HiddenInput,
			'property': HiddenInput
		}