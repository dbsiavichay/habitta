from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseBadRequest
from django.urls import reverse
from django.views.generic import RedirectView, TemplateView


from django.conf import settings
import paypalrestsdk

from realty.models import Property 
from .models import PaypalPayment

class PaypalView(RedirectView): 
	permanent = False

	def _generar_lista_items(self, property):	        
		items = []
		items.append({
			'name': str(property.category),
			'sku': str(property.id),
			'price': ('%.2f' % property.price),
			'currency': 'USD',
			'quantity': 1,
		})
		return items

	def _generar_peticion_pago_paypal(self, property):
		peticion_pago = {
			'intent': 'sale',
			'payer': {'payment_method': 'paypal'},
			'redirect_urls': {
				'return_url': 'http://localhost:5000'+reverse('aceptar_pago_paypal'),
				'cancel_url': 'http://localhost:5000'},

			# Transaction -
			'transactions': [ {
				# ItemList
				'item_list':{
					'items': self._generar_lista_items(property)},

				# Amount
				'amount': {
					'total': ('%.2f' % property.price),
					'currency': 'USD'},

				#Description
				'description': str(property),}
			]}
		return peticion_pago

	def _generar_pago_paypal(self, property):
		credentials = paypalrestsdk.Api({
			'mode': settings.PAYPAL_MODE,
			'client_id': settings.PAYPAL_CLIENT_ID,
			'client_secret': settings.PAYPAL_CLIENT_SECRET,
		})

		pago_paypal = paypalrestsdk.Payment(self._generar_peticion_pago_paypal(property), api=credentials)		

		if pago_paypal.create():
			for link in pago_paypal.links:
				if link.method == "REDIRECT":
					url_pago = link.href
		else:
			raise Exception(pago.error)

		return url_pago, pago_paypal

	def get_redirect_url(self, *args, **kwargs):
		"""Extrae el libro que el usuario quiere comprar, genera un pago de
		paypal por el precio del libro, y devuelve la direccion de pago que
		paypal generó"""
		property = get_object_or_404(Property, pk=int(kwargs['pk']))
		url_pago, pago_paypal = self._generar_pago_paypal(property)

		# Se añade el identificador del pago a la sesion para que PaypalExecuteView
		# pueda identificar al ususuario posteriorment
		self.request.session['payment_id'] = pago_paypal.id

		# Por ultimo salvar la informacion del pago para poder determinar que
		# libro le corresponde, al terminar la transaccion.
		PaypalPayment.objects.create(payment_id=pago_paypal.id, amount=property.price, property=property)

		return url_pago

class PaypalExecuteView(TemplateView):
	template_name = 'payments/paypal_exito.html'

	# def _enviar_ebook_email(self, registro_pago):
	# 	"""Enviar Email con el libro al cliente """
	# 	#TODO: adjuntar los archivos del modelo libro
	# 	libro = registro_pago.libro
	# 	mensaje = "Gracias por su compra de %s" % libro.titulo
	# 	send_mail('TiendaEbook', mensaje,
	# 		from_email = settings.DEFAULT_FROM_EMAIL,
	# 		recipient_list=[registro_pago.payer_email,])

	def completar_pago_paypal(self, payment_id, payer_id):
		"""Aceptar el pago del cliente, actualiza el registro con los datos
		del cliente proporcionados por paypal"""
		payment = get_object_or_404(PaypalPayment, payment_id=payment_id)
		paypal_payment = paypalrestsdk.Payment.find(payment_id)
		if paypal_payment.execute({'payer_id': payer_id}):
			payment.is_paid = True
			payment.payer_id = payer_id
			payment.payer_email = paypal_payment.payer['payer_info']['email']
			payment.save()
		else:
			raise HttpResponseBadRequest

		return payment

	def get(self, request, *args, **kwargs):
		"""Extraer identificacion de paypal del cliente, la id del pago,
		aceptar el pago, y enviar el email."""
		context = self.get_context_data(**kwargs)
		try:
			payer_id = request.GET['PayerID']
			payment_id = request.session['payment_id']
		except Exception:
			raise HttpResponseBadRequest

		payment = self.completar_pago_paypal(payment_id, payer_id)
		#self._enviar_ebook_email(payment)

		return self.render_to_response(context)