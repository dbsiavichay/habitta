from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
	CreateView, DeleteView, 
)
from .models import Image
from .forms import (
	ImageForm, 
)


def is_ajax(request):
	"""Reemplazo de HttpRequest.is_ajax() (removido en Django 4.0)."""
	return request.headers.get('x-requested-with') == 'XMLHttpRequest'


class Base64ImageUploadView(CreateView):
	model = Image	
	form_class = ImageForm
	http_method_names = ['post',]

	def form_valid(self, form):
		object_id = form.cleaned_data['object_id']
		content_type = form.cleaned_data['content_type']
		obj = content_type.get_object_for_this_type(pk=object_id)
		#Solo el propietario puede cambiar la foto de portada
		if obj.user != self.request.user:
			return JsonResponse({
					'error': 'No autorizado'
				}, status = 401
			)
		####
		self.object = form.save()

		return JsonResponse({
				'image_url': self.object.img.url,
				'delete_image_url': reverse_lazy('delete_image', args=[self.object.id]),
			}, 
			status=200
		)

	def form_invalid(self, form):		
		return JsonResponse({
			'error': form.errors
			}, status = 400
		)


class ImageDeleteView(DeleteView):
	model = Image
	http_method_names = ['post']

	def post(self, request, *args, **kwargs):
		if not is_ajax(request):
			raise Http404
		return super().post(request, *args, **kwargs)

	def form_valid(self, form):
		owner = getattr(self.object.get_object(), 'user', None)
		if owner != self.request.user:
			return JsonResponse({'error': 'No estás autorizado para realizar esta acción'}, status=403)
		self.object.delete()  # la señal post_delete borra el archivo
		return JsonResponse({}, status=200)
