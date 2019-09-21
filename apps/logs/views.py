from django.shortcuts import render, redirect
from django.views.generic import CreateView, DeleteView
from .models import Log
from .forms import LogForm

class LogCreateView(CreateView):
	model = Log
	form_class = LogForm

	def form_valid(self, form):
		property = form.cleaned_data['property']
		count = self.model.objects.filter(
			type=form.cleaned_data['type'], property=property, user=self.request.user
		).count()

		if count:
			return redirect(property.get_absolute_url())

		self.object = form.save(commit=False)
		self.object.user = self.request.user
		self.object.save()

		return redirect(property.get_absolute_url())

	def get(self, request, *args, **kwargs):
		raise Http404

class LogDeleteView(DeleteView):
	model = Log

	def delete(self, request, *args, **kwargs):
		self.object = self.get_object()
		self.success_url = self.object.property.get_absolute_url()
		self.object.delete()
		return redirect(self.success_url)

	def get(self, request, *args, **kwargs):
		raise Http404