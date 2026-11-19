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
		labels = {
			'amount': 'Monto que pagaste (USD)',
			'bank': 'Cuenta a la que pagaste',
			'voucher': 'Comprobante',
		}
		help_texts = {
			'voucher': 'Foto o PDF del depósito o la transferencia (JPG, PNG o PDF de hasta 5 MB).',
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['amount'].widget.attrs.update({'min': '0.01', 'step': '0.01', 'inputmode': 'decimal'})
		self.fields['voucher'].widget.attrs.update({'accept': '.pdf,.jpg,.jpeg,.png'})
		self.fields['bank'].empty_label = 'Elige la cuenta'

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