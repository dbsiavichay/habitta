from django.shortcuts import render
from django.views.generic import TemplateView, ListView
from datetime import timedelta

from django.utils import timezone
from apps.realty.models import Property, Purpose
from apps.auctions.models import Auction
from .models import Settings, Term, Help
from .mixins import ProjectMixin

class HomeView(ProjectMixin, TemplateView):
	template_name = 'index.html'

	def get_context_data(self, **kwargs):		
		context = super().get_context_data(**kwargs)
		properties = Property.objects.all()[:10]
		context.update({
			'properties':properties,
			'list_purposes': self.get_list_by_purposes(),
			'auctions':self.get_auctions_properties()
		})
		return context

	def get_list_by_purposes(self):
		result = []
		for purpose in Purpose.objects.all():
			properties = Property.objects.filter(details__purpose=purpose.id)[:10]
			if len(properties): result.append((purpose.activity, properties))
		return result

	def get_auctions_properties(self):
		Auction.objects.filter(ending_date__lte=timezone.now()+timedelta(minutes=1), stage=Auction.OPEN).update(stage=Auction.CLOSED)
		queryset = Property.objects.filter(auction__stage=Auction.OPEN)
		return queryset

class TermListView(ProjectMixin, ListView):
	model = Term
	template_name = 'project/terms.html'

class HelpListView(ProjectMixin, ListView):
	model = Help