from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from project.models import Settings
from .models import Service
from .mixins import ServiceViewMixin

from django.contrib.contenttypes.models import ContentType
from multimedia.forms import ImageForm

class ServiceListView(ListView):
	model = Service

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		try:
			settings = Settings.objects.get(is_active=True)
			context.update({'settings': settings})
		except Settings.DoesNotExist:
			pass
		return context

class UserServiceListView(ServiceListView):	
	template_name = 'services/userservice_list.html'

	def get_queryset(self):
		queryset = super().get_queryset()
		return queryset.filter(user=self.request.user)

class UserServiceCreateView(ServiceViewMixin, CreateView):
	template_name = 'services/userservice_form.html'
	
class UserServiceUpdateView(ServiceViewMixin, UpdateView):
	template_name = 'services/userservice_form.html'

	def get_cover_form(self):
		form = super().get_cover_form()
		if self.request.method == 'POST':		
			cover = self.get_object().get_cover_instance()			
			if cover:
				form.instance = cover
		return form

class UserServiceDeleteView(DeleteView):
	model = Service
	success_url = reverse_lazy('user_services')

class ServiceDetailView(DetailView):
	model = Service

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		self.object = self.get_object()	
		image_form = ImageForm(initial = {
			'object_id': self.object.id,
			'content_type': ContentType.objects.get_for_model(self.object)
		})		
		
		context.update({
			'image_form': image_form,				
		})

		return context