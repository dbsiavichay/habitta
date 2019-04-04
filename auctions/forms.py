from datetime import datetime

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

	def save(self, commit=True):
		obj = super().save(commit=False)

		obj.start_date = datetime.combine(
			self.cleaned_data['start_date'],
			self.cleaned_data['start_time']
		)
		obj.ending_date = datetime.combine(
			self.cleaned_data['ending_date'],
			self.cleaned_data['ending_time']
		)

		if commit:
			obj.save

		return obj