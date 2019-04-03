from django.shortcuts import render
from django.views.generic import CreateView
from .models import Auction
from .forms import AuctionForm

class AuctionCreateView(CreateView):
	model = Auction
	form_class = AuctionForm
	
