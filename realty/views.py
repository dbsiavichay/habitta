from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView

from .models import Property, Category
from .forms import PropertyForm, PropertyDetailsForm

class PropertyCreateView(CreateView):
	model = Property
	form_class = PropertyForm
	success_url = reverse_lazy('home')

	def form_valid(self, form):
		details_form = self.get_details_form()
		if not details_form.is_valid():
			return self.form_invalid(form)

		details = {
			'services': [service.id for service in form.cleaned_data['services']],
			'specifications': details_form.cleaned_data,
		}

		self.object = form.save(commit=False)
		self.object.user = self.request.user
		self.object.details = details
		self.object.category_id = 1
		self.object.save()
		#form.save_m2m()

		return redirect(self.success_url)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)		
		context.update({'details_form': self.get_details_form()})
		return context

	def get_details_form(self):
		post_data = self.request.POST if self.request.method == 'POST' else None		
		category = Category.objects.get(pk=1)
		form = PropertyDetailsForm(post_data, category=category)
		return form
	
	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs.update({'category': Category.objects.get(pk=1)})
		return kwargs

class PropertyUpdateView(UpdateView):
	model = Property
	form_class = PropertyForm
	success_url = reverse_lazy('home')
