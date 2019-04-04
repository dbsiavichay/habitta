from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView
from .models import Auction
from .forms import AuctionForm

from realty.models import Property

class AuctionCreateView(CreateView):
	model = Auction
	form_class = AuctionForm	

	def form_valid(self, form):
		self.object = form.save(commit=False)
		self.object.property = self.get_property()
		self.object.save()
		return redirect(reverse_lazy('detail_property', args=[self.object.property.id]))

	def get_property(self):
		pk = self.kwargs.get('pk') or self.request.GET.get('pk') or None
		property = get_object_or_404(Property, pk=pk)
		return property