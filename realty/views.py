from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse_lazy
from django.views.generic import (
	ListView, CreateView, UpdateView, DeleteView, DetailView, FormView
)

from multimedia.forms import ImageForm


from .models import Category, Property
from .forms import FinderForm
from .mixins import PropertyViewMixin

from logs.models import Log

class ChooseCategoryListView(ListView):
	model = Category
	queryset = Category.objects.filter(enabled=True)
	template_name = 'realty/choose_category.html'

class PropertyListView(ListView):
	model = Property

	def get_queryset(self):
		queryset = super().get_queryset()
		return queryset.filter(user=self.request.user)


class PropertyCreateView(PropertyViewMixin, CreateView):
	def get(self, request, *args, **kwargs):
		category = self.get_category()
		if not category.enabled:
			raise Http404
		return super().get(request, *args, **kwargs)

class PropertyUpdateView(PropertyViewMixin, UpdateView):	
	def get_details_form(self):
		form = super().get_details_form()
		if self.request.method == 'GET':
			try:
				initials = self.object.details['specifications']				
				form.initial = initials
			except KeyError:
				pass

		return form

	def get_cover_form(self):
		form = super().get_cover_form()
		if self.request.method == 'POST':		
			cover = self.get_object().get_cover_instance()			
			if cover:
				form.instance = cover
		return form

class PropertyDetailView(DetailView):
	model = Property

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		self.object = self.get_object()	
		image_form = ImageForm(initial = {
			'object_id': self.object.id,
			'content_type': ContentType.objects.get_for_model(self.object)
		})
		more_for_this_user = self.model.objects.filter(user=self.object.user).exclude(pk=self.object.pk)
		
		context.update({
			'image_form': image_form,
			'more_for_this_user': more_for_this_user,			
		})

		return context


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

