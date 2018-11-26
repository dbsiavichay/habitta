from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
	ListView, CreateView, UpdateView, DetailView, FormView,
)
from .models import Category, Property, PropertyImage
from .forms import (
	PropertyForm, PropertyDetailsForm,
	PropertyBase64ImageForm,
	FinderForm
)
from logs.models import Log

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

		return redirect(self.object.get_absolute_url())

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

class PropertyFavoriteListView(ListView):
	model = Property
	template_name_suffix = '_favorite_list'

	def get_queryset(self):
		properties = Log.objects.values_list('property_id', flat=True).filter(type=Log.LIKE, user=self.request.user)
		queryset = super().get_queryset()
		return queryset.filter(id__in=properties)

class FinderListView(FormView) :	
	template_name = 'realty/finder.html'
	form_class = FinderForm

	def post(self, request, *args, **kwargs):
		return self.get(request, *args, **kwargs)

