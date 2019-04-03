from django.forms import ( 
	ModelForm, Form, 
	ModelChoiceField, ModelMultipleChoiceField, 
	DateField, TimeField,
	ValidationError
)
from django.forms.widgets import (
	TextInput, NumberInput, HiddenInput,
	Select, RadioSelect,
	CheckboxSelectMultiple
)

from .models import Auction

class AuctionForm(ModelForm):
	class Meta:
		model = Auction
		fields = ('base_amount',)

	start_date = DateField(label='Fecha de inicio')
	start_time = TimeField(label='Hora de inicio')
	ending_date = DateField(label='Fecha de finalización')
	ending_time = TimeField(label='Hora de finalización')