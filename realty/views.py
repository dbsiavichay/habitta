from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
	ListView, CreateView, UpdateView, DeleteView, DetailView, FormView,
)
from .models import Category, Property, PropertyImage
from .forms import (
	PropertyForm, PropertyDetailsForm,
	PropertyBase64ImageForm,
	FinderForm
)
from logs.models import Log
from payments.models import PaypalPayment

import os
import zipfile
from io import BytesIO

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
			'purpose': form.cleaned_data['purpose'].id,
			'services': [service.id for service in form.cleaned_data['services']],
			'specifications': details_form.get_not_empty_cleaned_data(),
		}		

		self.object = form.save(commit=False)
		self.object.user = self.request.user
		self.object.details = details
		self.object.category = self.category
		self.object.save()		

		return redirect(self.object.get_absolute_url())

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)		
		context.update({
			'require_location': self.category.require_location,			
			'details_form': self.get_details_form()
		})
		return context

	def get_details_form(self):
		post_data = self.request.POST if self.request.method == 'POST' else None		
		files_data = self.request.FILES if self.request.method == 'POST' else None		
		form = PropertyDetailsForm(post_data, files_data, **{'category':self.category})
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
			'purpose': form.cleaned_data['purpose'].id,
			'services': [service.id for service in form.cleaned_data['services']],
			'specifications': details_form.get_not_empty_cleaned_data(),
		}

		self.object = form.save(commit=False)		
		self.object.details = details		
		self.object.save()
		#form.save_m2m()

		return redirect(self.success_url)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)	
		context.update({
			'require_location': self.object.category.require_location,			
			'details_form': self.get_details_form()
		})			
		return context

	def get_details_form(self):
		self.object = self.get_object()
		post_data = self.request.POST if self.request.method == 'POST' else None
		files_data = self.request.FILES if self.request.method == 'POST' else None
		kwargs = {'category':self.object.category}

		if self.request.method == 'GET':
			try:
				initials = self.object.details['specifications']
				kwargs.update({'initial': initials})
			except KeyError:
				pass

		form = PropertyDetailsForm(post_data, files_data,**kwargs)
		return form

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()		
		kwargs.update({'category': self.get_object().category})
		return kwargs

class PropertyDetailView(DetailView):
	model = Property

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		self.object = self.get_object()		
		image_form = PropertyBase64ImageForm(initial={'property':self.object})
		more_for_this_user = self.model.objects.filter(user=self.object.user).exclude(pk=self.object.pk)
		
		context.update({
			'image_form': image_form,
			'more_for_this_user': more_for_this_user,
			'auction':self.object.auction_set.first(),
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
				return redirect(reverse_lazy('detail_property', args=[property.id]))
			####
			self.form_valid(form, property)

			if request.is_ajax():
				return JsonResponse({
						'image_url': self.object.img.url,
						'delete_image_url': reverse_lazy('delete_property_image', args=[self.object.id]),
					}, 
					status=200
				)

			return redirect(reverse_lazy('detail_property', args=[property.id]))

		else:			
			return self.form_invalid(form)

	def get(self, request, *args, **kwargs):
		raise Http404

class PropertyImageDeleteView(DeleteView):
	model = PropertyImage
	http_method_names = ['post',]

	def delete(self, request, *args, **kwargs):		
		if not request.is_ajax():
			raise Http404
		self.object = self.get_object()	    
		if self.object.property.user != request.user:
			return JsonResponse({'message': 'No estas autorizado para realizar esta acción'}, status=403)
		self.object.delete()
		return JsonResponse({}, status=200)

class PropertyFavoriteListView(ListView):
	model = Property
	template_name_suffix = '_favorite_list'

	def get_queryset(self):
		properties = Log.objects.values_list('property_id', flat=True).filter(type=Log.LIKE, user=self.request.user)
		queryset = super().get_queryset()
		return queryset.filter(id__in=properties)

class PropertyDownloadListView(ListView):
	model = PaypalPayment
	template_name = 'realty/property_download_list.html'

	def get_queryset(self):
		queryset = super().get_queryset()
		return queryset.filter(user=self.request.user)

class PropertyDownloadView(DetailView):
	model = Property

	def render_to_response(self, context, **httpresponse_kwargs):		
		dirname = u'property_files_{0}'.format(self.object.id)
		filename = u'{0}.zip'.format(dirname)

		buffer = BytesIO()
		z = zipfile.ZipFile(buffer, 'w')

		for path in self.object.get_path_files():						
			z.write(path, os.path.join(dirname, os.path.basename(path)))
		z.close()
		buffer.seek(0)
		response = HttpResponse(buffer.read())
		response['Content-Disposition'] = u'attachment; filename={0}'.format(filename)
		response['Content-Type'] = 'application/x-zip'
		return response

	def get(self, request, *args, **kwargs):
		self.object = self.get_object()
		paypal = get_object_or_404(PaypalPayment, user=request.user, property=self.object)		
		if not paypal.is_paid: raise Http404
		return super().get(request, *args, **kwargs)

class FinderListView(FormView) :	
	template_name = 'realty/finder.html'
	form_class = FinderForm

	def post(self, request, *args, **kwargs):
		return self.get(request, *args, **kwargs)

