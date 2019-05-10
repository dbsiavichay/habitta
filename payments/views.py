from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseBadRequest, Http404
from django.urls import reverse, reverse_lazy
from django.views.generic import RedirectView, DetailView, ListView, CreateView


from django.conf import settings
import paypalrestsdk

from realty.models import Property 
from .models import Bank, BankPayment, PaypalPayment
from .forms import BankPaymentForm

class SelectMethodPaymentView(ListView):
	model = Bank
	template_name = 'payments/select_method_payment.html'

	def get(self, request, *args, **kwargs):		
		request.session['object_id'] = self.kwargs.get('pk')
		request.session['content_type'] =self.kwargs.get('ct')
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

class PaypalPaymentView(RedirectView): 
	permanent = False

	def get_items(self, property):	        
		items = []
		items.append({
			'name': str(property.category),
			'sku': str(property.id),
			'price': ('%.2f' % property.price),
			'currency': 'USD',
			'quantity': 1,
		})
		return items

	def get_paypal_kwargs(self, property):
		format_base_url = '%s://%s'
		base_url = format_base_url % ('https' if self.request.is_secure() else 'http', self.request.get_host())	
		kwargs = {
			'intent': 'sale',
			'payer': {'payment_method': 'paypal'},
			'redirect_urls': {
				'return_url': base_url+reverse('execute_paypal_payment'),
				'cancel_url': base_url},

			# Transaction -
			'transactions': [ {
				# ItemList
				'item_list':{
					'items': self.get_items(property)
				},

				# Amount
				'amount': {
					'total': ('%.2f' % property.price),
					'currency': 'USD'
				},

				#Description
				'description': str(property),
			}]
		}
		return kwargs

	def generate_paypal_payment(self, property):
		credentials = paypalrestsdk.Api({
			'mode': settings.PAYPAL_MODE,
			'client_id': settings.PAYPAL_CLIENT_ID,
			'client_secret': settings.PAYPAL_CLIENT_SECRET,
		})

		paypal_payment = paypalrestsdk.Payment(self.get_paypal_kwargs(property), api=credentials)		

		if paypal_payment.create():
			for link in paypal_payment.links:
				if link.method == "REDIRECT":
					url_payment = link.href
		else:
			raise Exception(paypal_payment.error)

		return url_payment, paypal_payment

	def get_redirect_url(self, *args, **kwargs):		
		property = get_object_or_404(Property, pk=int(kwargs['pk']))

		try:
			PaypalPayment.objects.get(user=self.request.user ,property=property)			
			raise Http404
		except PaypalPayment.DoesNotExist:
			pass
		url_payment, paypal_payment = self.generate_paypal_payment(property)

		# Se añade el identificador del pago a la sesion para que PaypalExecuteView
		# pueda identificar al ususuario posteriorment
		#self.request.session['payment_id'] = paypal_payment.id

		# Por ultimo salvar la informacion del pago para poder determinar que
		# libro le corresponde, al terminar la transaccion.
		PaypalPayment.objects.create(
			payment_id = paypal_payment.id, 
			amount = property.price, 
			user = self.request.user,
			property = property
		)

		return url_payment

class PaypalPaymentExecuteView(DetailView):
	model = PaypalPayment
	template_name = 'payments/paypal_successful.html'

	def execute_paypal_payment(self, payer_id):
		"""Aceptar el pago del cliente, actualiza el registro con los datos
		del cliente proporcionados por paypal"""		
		paypal_payment = paypalrestsdk.Payment.find(self.object.payment_id)
		if paypal_payment.execute({'payer_id': payer_id}):
			self.object.is_paid = True
			self.object.payer_id = payer_id
			self.object.payer_email = paypal_payment.payer['payer_info']['email']
			self.object.save()
		else:
			raise HttpResponseBadRequest		

	def get(self, request, *args, **kwargs):
		"""Extraer identificacion de paypal del cliente, la id del pago,
		aceptar el pago."""					
		self.object = self.get_object()
		if self.object.is_paid: raise Http404

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