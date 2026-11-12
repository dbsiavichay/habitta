from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.forms import ModelForm
from django.forms.widgets import HiddenInput
from .models import Payment, BankPayment

MAX_VOUCHER_BYTES = 5 * 1024 * 1024


class BankPaymentForm(ModelForm):
	class Meta:
		model = BankPayment
		fields = ('amount', 'bank', 'voucher')

	def clean_voucher(self):
		voucher = self.cleaned_data['voucher']
		FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])(voucher)
		if voucher.size > MAX_VOUCHER_BYTES:
			raise ValidationError('El comprobante supera el tamaño máximo de 5 MB.')
		return voucher

class PaymentForm(ModelForm):
	class Meta:
		model = Payment
		fields = ('amount', 'object_id', 'content_type')
		widgets = {
			'amount': HiddenInput,
			'object_id': HiddenInput,
			'content_type': HiddenInput,
		}