from datetime import timedelta

from django.utils import timezone

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

from .models import Auction, Offer

class AuctionForm(ModelForm):
	duration = IntegerField(
		min_value=1,
		max_value=24 * 90,
		label = 'Duración (horas)',
		help_text = 'Por ejemplo: 72 horas son 3 días; 168, una semana.',
	)

	def __init__(self, *args, **kwargs):
		user = kwargs.pop('user')
		super().__init__(*args, **kwargs)
		Auction.objects.filter(property__user=user).close_expired()
		queryset = self.fields['property'].queryset.filter(user=user).exclude(auction__stage=Auction.OPEN).select_related('category')
		self.fields['property'].queryset = queryset
		self.fields['property'].label = 'Anuncio a subastar'
		self.fields['property'].empty_label = 'Elige uno de tus anuncios'
		self.fields['base_amount'].label = 'Monto base (USD)'
		self.fields['base_amount'].help_text = 'La oferta más baja que aceptas. Quien participe deja una garantía del 10 %.'
		self.fields['base_amount'].widget.attrs.update({'min': '1', 'step': '0.01', 'inputmode': 'decimal'})

	def save(self, commit=True):
		obj = super().save(commit=False)
		now = timezone.now()
		obj.start_date = now
		obj.ending_date = now + timedelta(hours=self.cleaned_data['duration'])
		if commit:
			obj.save()

		return obj

	class Meta:
		model = Auction
		fields = ('property','base_amount','duration')

class OfferForm(ModelForm):
	class Meta:
		model = Offer
		fields = ('amount', 'auction')
		widgets = {
			'auction': HiddenInput,
		}
