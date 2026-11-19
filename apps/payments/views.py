import logging
import os
import zipfile
from decimal import Decimal, InvalidOperation
from io import BytesIO

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, RedirectView

from . import paypal
from .forms import BankPaymentForm, PaymentForm
from .models import Bank, BankPayment, Payment, PaypalPayment

logger = logging.getLogger(__name__)


def get_server_price(obj):
	"""Precio del objeto calculado en el servidor (nunca se confía en el cliente)."""
	try:
		price = Decimal(str(obj.get_price_area()))
	except (InvalidOperation, TypeError, ValueError, AttributeError):
		return None
	return price if price > 0 else None


class SelectMethodPaymentView(ListView):
	model = Bank
	template_name = 'payments/select_method_payment.html'

	def get(self, request, *args, **kwargs):
		request.session['object_id'] = self.kwargs.get('pk')
		request.session['content_type'] = self.kwargs.get('ct')
		return super().get(request, *args, **kwargs)

def get_pending_payment(request):
	"""Lo que el usuario está por pagar (lo guarda MethodPaymentListView en la sesión), o None."""
	object_id = request.session.get('object_id')
	content_type_id = request.session.get('content_type')
	if not object_id or not content_type_id:
		return None
	try:
		obj = ContentType.objects.get_for_id(content_type_id).get_object_for_this_type(pk=object_id)
	except (ObjectDoesNotExist, AttributeError):
		return None
	return {'object': obj, 'amount': request.session.get('amount')}


class MethodPaymentListView(ListView):
	model = Bank
	template_name = 'payments/select_method_payment.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['pending'] = get_pending_payment(self.request)
		return context

	def post(self, request, *args, **kwargs):
		form = PaymentForm(self.request.POST)
		if not form.is_valid():
			return HttpResponseBadRequest('Datos de pago inválidos')

		content_type = form.cleaned_data['content_type']
		object_id = form.cleaned_data['object_id']
		try:
			obj = content_type.get_object_for_this_type(pk=object_id)
		except content_type.model_class().DoesNotExist:
			raise Http404

		price = get_server_price(obj)
		if price is None:
			return HttpResponseBadRequest('Este elemento no tiene un precio válido')

		request.session['amount'] = str(price)
		request.session['object_id'] = obj.pk
		request.session['content_type'] = content_type.id
		return super().get(request, *args, **kwargs)

class BankPaymentListView(ListView):
	"""Mis pagos: transferencias y PayPal, con su estado."""
	model = Payment
	template_name = 'payments/bankpayment_list.html'
	paginate_by = 12

	def get_queryset(self):
		return (
			Payment.objects.filter(user=self.request.user)
			.select_related('content_type', 'bankpayment__bank', 'paypalpayment')
			.order_by('-date', '-pk')
		)

class BankPaymentCreateView(CreateView):
	model = BankPayment
	form_class = BankPaymentForm
	success_url = reverse_lazy('list_bank_payment')

	def get_initial(self):
		initial = super().get_initial()
		# El monto lo calculó el servidor al elegir el método de pago
		if self.request.session.get('amount'):
			initial['amount'] = self.request.session['amount']
		return initial

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['pending'] = get_pending_payment(self.request)
		return context

	def form_valid(self, form):
		object_id = self.request.session.pop('object_id', None)
		content_type = self.request.session.pop('content_type', None)
		self.request.session.pop('amount', None)
		if not object_id or not content_type:
			return HttpResponseBadRequest('No hay un pago en curso')
		self.object = form.save(commit=False)
		self.object.user = self.request.user
		self.object.object_id = object_id
		self.object.content_type_id = content_type
		self.object.save()
		messages.success(self.request, 'Registramos tu pago. Te avisaremos cuando lo confirmemos.')
		return redirect(self.get_success_url())

class PaypalPaymentExecuteView(DetailView):
	"""PayPal redirige aquí (``?token=<order_id>&PayerID=...``) tras aprobar el pago."""
	model = PaypalPayment
	template_name = 'payments/paypal_successful.html'

	def get_object(self, queryset=None):
		order_id = self.request.GET.get('token')
		if not order_id:
			raise Http404
		return get_object_or_404(PaypalPayment, payment_id=order_id, user=self.request.user)

	def get(self, request, *args, **kwargs):
		self.object = self.get_object()
		if self.object.is_confirmed():
			raise Http404

		try:
			order = paypal.capture_order(self.object.payment_id)
		except paypal.PayPalError:
			logger.exception('No se pudo capturar la orden de PayPal %s', self.object.payment_id)
			return HttpResponseBadRequest('No se pudo completar el pago con PayPal')

		if order.get('status') != 'COMPLETED' or paypal.captured_amount(order) < self.object.amount:
			self.object.status = Payment.REJECTED
			self.object.save(update_fields=['status'])
			return HttpResponseBadRequest('El pago no fue completado')

		payer = order.get('payer', {})
		self.object.status = Payment.CONFIRMED
		self.object.payer_id = payer.get('payer_id', '')
		self.object.payer_email = payer.get('email_address', '')
		self.object.save()

		context = self.get_context_data(object=self.object)
		return self.render_to_response(context)

class PaypalPaymentCreateView(RedirectView):
	permanent = False

	def get(self, request, *args, **kwargs):
		if not paypal.is_configured():
			raise Http404
		return super().get(request, *args, **kwargs)

	def get_object_from_session(self):
		session = self.request.session
		try:
			amount = Decimal(session.pop('amount'))
			content_type = ContentType.objects.get(pk=session.pop('content_type'))
			obj = content_type.get_object_for_this_type(pk=session.pop('object_id'))
		except Exception:
			raise Http404
		return amount, obj, content_type

	def get_redirect_url(self, *args, **kwargs):
		amount, obj, content_type = self.get_object_from_session()
		user = self.request.user
		lookup = {'user': user, 'object_id': obj.pk, 'content_type': content_type}

		if PaypalPayment.objects.filter(status=Payment.CONFIRMED, **lookup).exists():
			raise Http404

		base_url = self.request.build_absolute_uri('/')[:-1]
		try:
			order_id, approve_url = paypal.create_order(
				amount=amount,
				description=str(obj),
				reference_id=obj.pk,
				return_url=base_url + reverse('execute_paypal_payment'),
				cancel_url=base_url + obj.get_absolute_url(),
			)
		except paypal.PayPalError:
			logger.exception('No se pudo crear la orden de PayPal')
			raise Http404

		# Reutiliza un pago pendiente (orden anterior no aprobada) o crea uno nuevo.
		pending = PaypalPayment.objects.filter(status=Payment.REGISTRY, **lookup).first()
		if pending:
			pending.payment_id = order_id
			pending.amount = amount
			pending.save(update_fields=['payment_id', 'amount'])
		else:
			PaypalPayment.objects.create(payment_id=order_id, amount=amount, **lookup)
		return approve_url

class DownloadListView(ListView):
	"""Archivos comprados: se descargan cuando el pago está confirmado."""
	model = Payment
	template_name = 'payments/download_list.html'
	paginate_by = 12

	def get_queryset(self):
		return (
			Payment.objects.filter(user=self.request.user)
			.exclude(status=Payment.REJECTED)
			.select_related('content_type')
			.order_by('-date', '-pk')
		)

class DownloadView(DetailView):
	model = Payment

	def get_queryset(self):
		return super().get_queryset().filter(user=self.request.user, status=Payment.CONFIRMED)

	def render_to_response(self, context, **httpresponse_kwargs):		
		dirname = u'download_files_{0}'.format(self.object.id)
		filename = u'{0}.zip'.format(dirname)

		buffer = BytesIO()
		z = zipfile.ZipFile(buffer, 'w')

		for path in self.object.get_object().get_path_files():						
			z.write(path, os.path.join(dirname, os.path.basename(path)))
		z.close()
		buffer.seek(0)
		response = HttpResponse(buffer.read())
		response['Content-Disposition'] = u'attachment; filename={0}'.format(filename)
		response['Content-Type'] = 'application/x-zip'
		return response

	def get(self, request, *args, **kwargs):
		self.object = self.get_object()
		return self.render_to_response({})