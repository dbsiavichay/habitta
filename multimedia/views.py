from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
	CreateView, DeleteView, 
)
from .models import Image
from .forms import (
	Base64ImageForm, 
)

class Base64ImageUploadView(CreateView):
	model = Image	
	form_class = Base64ImageForm

	def form_valid(self, form, obj):
		# Para que el form elimine la imagen cover anterior
		if form.cleaned_data['is_cover']:
			instance = obj.get_cover_instance()
			if instance: form.instance = instance				

		self.object = form.save();					

	def post(self, request, *args, **kwargs):
		form = self.get_form()
		if form.is_valid():
			object_id = form.cleaned_data['object_id']
			content_type = form.cleaned_data['content_type']
			obj = content_type.get_object_for_this_type(pk=object_id)
			#Solo el propietario puede cambiar la foto de portada
			if obj.user != request.user:
				return redirect(reverse_lazy('detail_property', args=[object_id]))
			####
			self.form_valid(form, obj)

			if request.is_ajax():
				return JsonResponse({
						'image_url': self.object.img.url,
						'delete_image_url': reverse_lazy('delete_image', args=[self.object.id]),
					}, 
					status=200
				)

			return redirect(reverse_lazy('detail_property', args=[object_id]))

		else:			
			return self.form_invalid(form)

	def get(self, request, *args, **kwargs):
		raise Http404

class ImageDeleteView(DeleteView):
	model = Image
	http_method_names = ['post',]

	def delete(self, request, *args, **kwargs):		
		if not request.is_ajax():
			raise Http404
		self.object = self.get_object()	    
		if self.object.get_object().user != request.user:
			return JsonResponse({'message': 'No estas autorizado para realizar esta acción'}, status=403)
		if self.object.img:
			self.object.img.delete()
		self.object.delete()
		return JsonResponse({}, status=200)
