from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView

from .models import Category, Property, PropertyImage
from .forms import (
	PropertyForm, PropertyDetailsForm,
	PropertyBase64ImageForm
)

class ChooseCategoryListView(ListView):
	model = Category
	template_name = 'realty/choose_category.html'

class PropertyListView(ListView):
	model = Property

	def get_queryset(self):
		queryset = super().get_queryset()
		return queryset.filter(user=self.request.user)

class PropertyCreateView(CreateView):
	model = Property
	form_class = PropertyForm
	success_url = reverse_lazy('properties')

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
		self.object.category = self.category
		self.object.save()
		#form.save_m2m()

		return redirect(self.success_url)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)		
		context.update({'details_form': self.get_details_form()})
		return context

	def get_details_form(self):
		post_data = self.request.POST if self.request.method == 'POST' else None		
		form = PropertyDetailsForm(post_data, **{'category':self.category})
		return form
	
	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		self.category = get_object_or_404(Category, pk=self.kwargs.get('category'))		
		kwargs.update({'category': self.category})
		return kwargs

class PropertyUpdateView(UpdateView):
	model = Property
	form_class = PropertyForm
	success_url = reverse_lazy('properties')

	def form_valid(self, form):
		details_form = self.get_details_form()
		if not details_form.is_valid():
			return self.form_invalid(form)

		details = {
			'services': [service.id for service in form.cleaned_data['services']],
			'specifications': details_form.cleaned_data,
		}

		self.object = form.save(commit=False)		
		self.object.details = details		
		self.object.save()
		#form.save_m2m()

		return redirect(self.success_url)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)		
		context.update({'details_form': self.get_details_form()})
		return context

	def get_details_form(self):
		self.object = self.get_object()
		post_data = self.request.POST if self.request.method == 'POST' else None
		kwargs = {'category':self.object.category}

		if self.request.method == 'GET':
			initials = self.object.details['specifications']
			kwargs.update({'initial': initials})

		form = PropertyDetailsForm(post_data, **kwargs)
		return form

class PropertyDetailView(DetailView):
	model = Property

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		self.object = self.get_object()		
		image_form = PropertyBase64ImageForm(initial={'property':self.object})
		
		context.update({
			'image_form': image_form,
		})

		return context

class PropertyBase64ImageUploadView(CreateView):
	model = PropertyImage	
	form_class = PropertyBase64ImageForm

	def form_valid(self, form, property):
		if form.cleaned_data['is_cover']:
			instance = property.get_cover_instance()
			if instance: form.instance = instance				

		self.object = form.save();					

	def post(self, request, *args, **kwargs):
		form = self.get_form()
		if form.is_valid():
			property = form.cleaned_data['property']
			#Solo el propietario puede cambiar la foto de portada
			if property.user != request.user:
				return redirect(reverse_lazy('detail_local', args=[property.id]))
			####
			self.form_valid(form, property)

			if request.is_ajax():
				return JsonResponse({'image_url': self.object.img.url}, status=200)

			return redirect(reverse_lazy('detail_property', args=[property.id]))

		else:			
			return self.form_invalid(form)

	def get(self, request, *args, **kwargs):
		raise Http404

class FinderListView(ListView):
	model = Property
	template_name = 'realty/finder.html'

	def get(self, request, *args, **kwargs):
		if request.is_ajax():
			_list = []
			for obj in self.get_queryset():
				data = {
					'url': reverse_lazy('detail_property', args=[obj.id]),
					'category': obj.category.name,
					'cover': obj.get_cover(),
					'activity': obj.purpose.activity,
					'address': obj.address,
					'phone': obj.user.profile.phone,
					'stars': 4,
					'reviews': 11,
					'longitude': obj.geopoint.x,
					'latitude': obj.geopoint.y
				}

				_list.append(data)

			return JsonResponse(_list, safe=False)

		return super().get(request, *args, **kwargs)


class HomeView(TemplateView):
	template_name = 'index.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		properties = Property.objects.all()
		context.update({'properties':properties})
		return context