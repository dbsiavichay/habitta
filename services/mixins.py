from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.contrib.contenttypes.models import ContentType
from .models import Service
from .forms import ServiceForm
from multimedia.forms import CoverImageForm

class ServiceViewMixin(object):
	model = Service
	form_class = ServiceForm
	success_url = reverse_lazy('user_services')

	def form_valid(self, form):
		cover_form = self.get_cover_form()
		if not cover_form.is_valid():
			return self.form_invalid(form)
		self.object = form.save(commit=False)
		self.object.user = self.request.user
		self.object.save()
		self.save_cover(cover_form, self.object)
		return redirect(self.success_url)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)		
		context.update({								
			'cover_form': self.get_cover_form()
		})			
		return context

	def get_cover_form(self):		
		post_data = self.request.POST if self.request.method == 'POST' else None
		files_data = self.request.FILES if self.request.method == 'POST' else None
		form = CoverImageForm(post_data, files_data)
		return form

	def save_cover(self, form, obj):
		cover = form.save(commit=False)
		if cover:
			cover.object_id = obj.id
			cover.content_type = ContentType.objects.get_for_model(obj)
			cover.save()