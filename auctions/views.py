from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView
from .models import Auction, Offer
from .forms import AuctionForm

from realty.models import Property

class AuctionListView(ListView):
	model = Auction

class AuctionCreateView(CreateView):
	model = Auction
	form_class = AuctionForm	
	success_url = reverse_lazy('auctions')

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs.update({'user':self.request.user})		
		return kwargs
