from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView
from .models import Auction, Offer
from .forms import AuctionForm, OfferForm

from apps.realty.models import Property

class AuctionListView(ListView):
	model = Auction

class AuctionCreateView(CreateView):
	model = Auction
	form_class = AuctionForm	
	success_url = reverse_lazy('auctions')

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		property = self.request.GET.get('id', None)
		kwargs.update({'user':self.request.user, 'initial': {'property':property}})		
		return kwargs

class OfferCreateView(CreateView):
	model = Offer
	form_class = OfferForm

	def form_valid(self, form):
		self.object = form.save(commit=False)
		self.object.user = self.request.user
		self.object.save()
		return redirect(self.object.auction.get_absolute_url())