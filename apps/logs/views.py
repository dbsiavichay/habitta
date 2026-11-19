from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.views.generic import CreateView, DeleteView

from .forms import LogForm
from .models import Log
from .templatetags.logs import render_like


class LogCreateView(CreateView):
	model = Log
	form_class = LogForm

	def form_valid(self, form):
		property = form.cleaned_data['property']
		exists = self.model.objects.filter(
			type=form.cleaned_data['type'], property=property, user=self.request.user
		).exists()

		if not exists:
			self.object = form.save(commit=False)
			self.object.user = self.request.user
			self.object.save()

		if self.request.htmx:
			return HttpResponse(render_like(property, self.request.user, self.request))
		return redirect(property.get_absolute_url())

	def get(self, request, *args, **kwargs):
		raise Http404

class LogDeleteView(DeleteView):
	model = Log
	http_method_names = ['post']

	def get_queryset(self):
		return super().get_queryset().filter(user=self.request.user)

	def form_valid(self, form):
		property = self.object.property
		self.object.delete()
		if self.request.htmx:
			return HttpResponse(render_like(property, self.request.user, self.request))
		return redirect(property.get_absolute_url())
