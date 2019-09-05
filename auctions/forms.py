from datetime import datetime, timedelta

from django.forms import ( 
	ModelForm, Form, 
	ModelChoiceField, ModelMultipleChoiceField, 
	DateField, TimeField, IntegerField,
	ValidationError
)
from django.forms.widgets import (
	TextInput, NumberInput, HiddenInput,
	Select, RadioSelect,
	CheckboxSelectMultiple
)

from .models import Auction

class AuctionForm(ModelForm):
	duration = IntegerField(
		min_value=1,
		label = 'Duración en horas'
	)

	def __init__(self, *args, **kwargs):
		user = kwargs.pop('user')
		super().__init__(*args, **kwargs)
		Auction.objects.filter(property__user=user, ending_date__lte=datetime.now()+timedelta(minutes=1), stage=Auction.OPEN).update(stage=Auction.CLOSED)
		queryset = self.fields['property'].queryset.filter(user=user).exclude(auction__stage=Auction.OPEN)
		self.fields['property'].queryset = queryset

	def save(self, commit=True):
		obj = super().save(commit=False)
		now = datetime.now()
		obj.start_date = now
		obj.ending_date = now + timedelta(hours=self.cleaned_data['duration'])
		if commit:
			obj.save()

		return obj

	class Meta:
		model = Auction
		fields = ('property','base_amount','duration')
