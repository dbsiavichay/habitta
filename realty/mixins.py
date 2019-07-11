from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.contenttypes.models import ContentType
from .models import Property, Category
from .forms import PropertyForm, PropertyDetailsForm, PropertyDetailsForm2
from multimedia.forms import CoverImageForm
from project.models import Icons

class PropertyViewMixin(object):
	model = Property
	form_class = PropertyForm
	success_url = reverse_lazy('properties')

	def form_valid(self, form):
		details_form = self.get_details_form()
		cover_form = self.get_cover_form()
		if not details_form.is_valid() or not cover_form.is_valid():
			return self.form_invalid(form)

		details = {
			'purpose': form.cleaned_data['purpose'].id,
			'services': [service.id for service in form.cleaned_data['services']],
			'specifications': details_form.get_not_empty_cleaned_data(),
		}	

		self.object = form.save(commit=False)
		self.object.details = details
		if not hasattr(self.object, 'user'):
			self.object.user = self.request.user
		self.object.category = self.category
		self.object.save()

		self.save_cover(cover_form, self.object)
		return redirect(self.object.get_absolute_url())

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)		
		context.update({
			'require_location': self.category.require_location,			
			'details_form': self.get_details_form(),
			'cover_form': self.get_cover_form(),
			'icons_url': get_active_icons_url()
		})			
		return context
	
	def get_category(self):
		pk = self.kwargs.get('category')
		if pk is not None:    	
			category = get_object_or_404(Category, pk=pk)
		else:
			category = self.get_object().category

		return category

	def get_form_kwargs(self):
		self.category = self.get_category()	
		kwargs = super().get_form_kwargs()	
		kwargs.update({'category': self.category})
		return kwargs

	def get_details_form(self):	
		form = PropertyDetailsForm2(**self.get_kwargs(category=self.category))
		return form

	def get_cover_form(self):				
		form = CoverImageForm(**self.get_kwargs())
		return form

	def get_kwargs(self, **kwargs):
		if self.request.method in ('POST', 'PUT'):
			kwargs.update({
				'data': self.request.POST,
				'files': self.request.FILES,
			})
		return kwargs

	def save_cover(self, form, obj):
		cover = form.save(commit=False)
		if cover:
			cover.object_id = obj.id
			cover.content_type = ContentType.objects.get_for_model(obj)
			cover.save()

def get_active_icons_url():
	try:
		icons = Icons.objects.get(is_active=True)
		return icons.css.url
	except Icons.DoesNotExist:
		return ''