from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from project.models import Settings
from .models import Service
from .forms import ServiceForm

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

class UserServiceCreateView(CreateView):
	model = Service
	form_class = ServiceForm
	template_name = 'services/userservice_form.html'
	success_url = reverse_lazy('user_services')

	def form_valid(self, form):
		self.object = form.save(commit=False)
		self.object.user = self.request.user
		self.object.save()
		return redirect(self.success_url)

class UserServiceUpdateView(UpdateView):
	model = Service
	form_class = ServiceForm
	template_name = 'services/userservice_form.html'
	success_url = reverse_lazy('user_services')

class UserServiceDeleteView(DeleteView):
	model = Service
	success_url = reverse_lazy('user_services')