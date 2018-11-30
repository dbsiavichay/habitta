from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView
from .models import Service
from .forms import ServiceForm

class ServiceListView(ListView):
	model = Service

class UserServiceListView(ServiceListView):	
	template_name = 'services/userservice_list.html'

	def get_queryset(self):
		queryset = super().get_queryset()
		return queryset.filter(user=self.request.user)

class UserServiceCreateView(CreateView):
	model = Service
	form_class = ServiceForm
	template_name = 'services/userservice_form.html'

	def form_valid(self, form):
		self.object = form.save(commit=False)
		self.object.user = self.request.user
		self.object.save()
		return redirect('user_services')

class UserServiceUpdateView(UpdateView):
	model = Service
	form_class = ServiceForm
	success_url = reverse_lazy('user_services')