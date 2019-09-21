from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.urls import reverse, reverse_lazy
from django.views.generic import RedirectView, DetailView, ListView, CreateView

from django.contrib.contenttypes.models import ContentType
from django.conf import settings
import paypalrestsdk

from apps.realty.models import Property 
from .models import Bank, Payment, BankPayment, PaypalPayment
from .forms import PaymentForm, BankPaymentForm

#For download object
import os
import zipfile
from io import BytesIO

class SelectMethodPaymentView(ListView):
	model = Bank
	template_name = 'payments/select_method_payment.html'

	def get(self, request, *args, **kwargs):		
		request.session['object_id'] = self.kwargs.get('pk')
		request.session['content_type'] =self.kwargs.get('ct')
		return super().get(request, *args, **kwargs)

class MethodPaymentListView(ListView):
	model = Bank
	template_name = 'payments/select_method_payment.html'

	def post(self, request, *args, **kwargs):
		form = PaymentForm(self.request.POST)
		if form.is_valid():			
			request.session['amount'] = str(form.cleaned_data['amount'])
			request.session['object_id'] = form.cleaned_data['object_id']
			request.session['content_type'] = form.cleaned_data['content_type'].id
		return super().get(request, *args, **kwargs)

class BankPaymentListView(ListView):
	model = BankPayment

	def get_queryset(self):
		queryset = super().get_queryset()
		queryset = queryset.filter(user=self.request.user)
		return queryset

class BankPaymentCreateView(CreateView):
	model = BankPayment
	form_class = BankPaymentForm
	success_url = reverse_lazy('list_bank_payment')

	def form_valid(self, form):
		object_id = self.request.session.pop('object_id', None)
		content_type = self.request.session.pop('content_type', None)
		self.object = form.save(commit=False)
		self.object.user = self.request.user
		self.object.object_id = object_id
		self.object.content_type_id = content_type
		self.object.save()	

class PaypalPaymentExecuteView(DetailView):
	model = PaypalPayment
	template_name = 'payments/paypal_successful.html'

	def execute_paypal_payment(self, payer_id):
		"""Aceptar el pago del cliente, actualiza el registro con los datos
		del cliente proporcionados por paypal"""		
		paypal_payment = paypalrestsdk.Payment.find(self.object.payment_id)
		if paypal_payment.execute({'payer_id': payer_id}):
			self.object.status = Payment.CONFIRMED
			self.object.payer_id = payer_id
			self.object.payer_email = paypal_payment.payer['payer_info']['email']
			self.object.save()
		else:
			raise HttpResponseBadRequest		

	def get(self, request, *args, **kwargs):
		"""Extraer identificacion de paypal del cliente, la id del pago,
		aceptar el pago."""					
		self.object = self.get_object()
		if self.object.is_confirmed():
			raise Http404

		try:			
			payer_id = request.GET['PayerID']
		except Exception:
			raise HttpResponseBadRequest

		self.execute_paypal_payment(payer_id)		
		context = self.get_context_data(object=self.object)
		return self.render_to_response(context)

	def get_object(self):
		try:			
			payment_id = self.request.GET['paymentId']
			return get_object_or_404(PaypalPayment, payment_id=payment_id)
		except:
			raise HttpResponseBadRequest

class PaypalPaymentCreateView(RedirectView):
	permanent = False

	def get_items(self, obj, amount):
		items = []
		items.append({
			'name': str(obj),
			'sku': str(obj.id),
			'price': ('%.2f' % amount),
			'currency': 'USD',
			'quantity': 1,
		})
		return items

	def get_paypal_kwargs(self, obj, amount):
		format_base_url = '%s://%s'
		base_url = format_base_url % ('https' if self.request.is_secure() else 'http', self.request.get_host())
		kwargs = {
			'intent': 'sale',
			'payer': {'payment_method': 'paypal'},
			'redirect_urls': {
				'return_url': base_url+reverse('execute_paypal_payment'),
				'cancel_url': base_url
			},

			# Transaction -
			'transactions': [ {
				# ItemList
				'item_list':{
					'items': self.get_items(obj, amount)
				},

				# Amount
				'amount': {
					'total': ('%.2f' % amount),
					'currency': 'USD'
				},

				#Description
				'description': str(obj),
			}]
		}
		return kwargs

	def generate_paypal_payment(self, obj, amount):
		credentials = paypalrestsdk.Api({
			'mode': settings.PAYPAL_MODE,
			'client_id': settings.PAYPAL_CLIENT_ID,
			'client_secret': settings.PAYPAL_CLIENT_SECRET,
		})

		paypal_payment = paypalrestsdk.Payment(self.get_paypal_kwargs(obj, amount), api=credentials)		

		if paypal_payment.create():
			for link in paypal_payment.links:
				if link.method == "REDIRECT":
					url_payment = link.href
		else:
			raise Exception(paypal_payment.error)

		return url_payment, paypal_payment

	def get_object_from_session(self):
		object_id = self.request.session.pop('object_id', None)
		content_type_id = self.request.session.pop('content_type', None)
		amount = float(self.request.session.pop('amount'))
		content_type =  ContentType.objects.get(pk=content_type_id)
		obj = content_type.get_object_for_this_type(pk=object_id)
		return amount, obj, content_type

	def get_redirect_url(self, *args, **kwargs):
		amount, obj, content_type= self.get_object_from_session()
		user = self.request.user	
		kwargs = {
			'object_id': obj.id, 
			'content_type': content_type
		}
		try:
			PaypalPayment.objects.filter(user=user).exclude(status=Payment.REJECTED).get(**kwargs)						
			raise Http404
		except PaypalPayment.DoesNotExist:
			url_payment, paypal_payment = self.generate_paypal_payment(obj, amount)
			kwargs.update({
				'payment_id': paypal_payment.id,
				'amount': amount,
				'user': user				
			})

		# Se añade el identificador del pago a la sesion para que PaypalExecuteView
		# pueda identificar al ususuario posteriorment
		#self.request.session['payment_id'] = paypal_payment.id

		# Por ultimo salvar la informacion del pago para poder determinar que
		# libro le corresponde, al terminar la transaccion.

		PaypalPayment.objects.create(**kwargs)
		return url_payment

class DownloadListView(ListView):
	model = Payment
	template_name = 'payments/download_list.html'

	def get_queryset(self):
		queryset = super().get_queryset()
		return queryset.filter(user=self.request.user)

class DownloadView(DetailView):
	model = Payment

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
		if not self.object.is_confirmed(): raise Http404
		return super().get(request, *args, **kwargs)