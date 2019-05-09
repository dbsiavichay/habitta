from django.forms import ModelForm
from .models import BankPayment

class BankPaymentForm(ModelForm):
	class Meta:
		model = BankPayment
		fields = ('amount', 'bank', 'voucher')