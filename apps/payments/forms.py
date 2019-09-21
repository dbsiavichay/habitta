from django.forms import ModelForm
from django.forms.widgets import HiddenInput
from .models import Payment, BankPayment

class BankPaymentForm(ModelForm):
	class Meta:
		model = BankPayment
		fields = ('amount', 'bank', 'voucher')

class PaymentForm(ModelForm):
	class Meta:
		model = Payment
		fields = ('amount', 'object_id', 'content_type')
		widgets = {
			'amount': HiddenInput,
			'object_id': HiddenInput,
			'content_type': HiddenInput,
		}