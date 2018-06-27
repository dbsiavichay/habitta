from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView

from .models import Property, Category
from .forms import PropertyForm

class PropertyCreateView(CreateView):
	model = Property
	form_class = PropertyForm
	success_url = reverse_lazy('home')

	def form_valid(self, form):
		self.object = form.save(commit=False)
		self.object.user = self.request.user
		self.object.save()
		form.save_m2m()

		return redirect(self.success_url)
	
	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs.update({'category': Category.objects.get(pk=1)})
		return kwargs

class PropertyUpdateView(UpdateView):
	model = Property
	form_class = PropertyForm
	success_url = reverse_lazy('home')
