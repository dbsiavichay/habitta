from django.contrib import messages
from django.db.models import Count, Max
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.formats import date_format
from django.views import View
from django.views.generic import ListView, CreateView

from .models import Auction, Offer
from .forms import AuctionForm, OfferForm


class AuctionListView(ListView):
	"""Subastas de los anuncios del usuario."""
	model = Auction
	paginate_by = 12

	def get_queryset(self):
		auctions = Auction.objects.filter(property__user=self.request.user)
		auctions.close_expired()
		return (
			auctions.select_related('property__category')
			.annotate(offers_count=Count('offer'), best_offer=Max('offer__amount'))
			.order_by('-start_date', '-pk')
		)


class AuctionCreateView(CreateView):
	model = Auction
	form_class = AuctionForm
	success_url = reverse_lazy('auctions')

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		property = self.request.GET.get('id', None)
		kwargs.update({'user':self.request.user, 'initial': {'property':property}})
		return kwargs

	def form_valid(self, form):
		response = super().form_valid(form)
		ending = date_format(timezone.localtime(self.object.ending_date), r'j \d\e F \a \l\a\s H:i')
		messages.success(self.request, 'Tu subasta está abierta hasta el %s.' % ending)
		return response


class AuctionCancelView(View):
	"""Cancela una subasta abierta de un anuncio propio."""
	http_method_names = ['post']

	def post(self, request, pk):
		auction = get_object_or_404(Auction.objects.select_related('property'), pk=pk, property__user=request.user)
		if auction.stage == Auction.OPEN:
			auction.stage = Auction.CANCELED
			auction.save(update_fields=['stage'])
			messages.success(request, 'Cancelaste la subasta de «%s».' % auction.property)
		else:
			messages.info(request, 'Esa subasta ya no estaba abierta.')
		return redirect('auctions')


class OfferCreateView(CreateView):
	model = Offer
	form_class = OfferForm

	def form_valid(self, form):
		self.object = form.save(commit=False)
		self.object.user = self.request.user
		self.object.save()
		return redirect(self.object.auction.get_absolute_url())
