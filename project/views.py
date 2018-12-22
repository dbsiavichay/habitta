from django.shortcuts import render
from django.views.generic import TemplateView, ListView

from realty.models import Property
from.models import Settings, Term, Help

class HomeView(TemplateView):
	template_name = 'index.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		properties = Property.objects.all()
		try:
			settings = Settings.objects.get(is_active=True)
			context.update({'settings': settings})
		except Settings.DoesNotExist:
			pass
		context.update({'properties':properties})
		return context

class TermListView(ListView):
	model = Term
	template_name = 'project/terms.html'

class HelpListView(ListView):
	model = Help