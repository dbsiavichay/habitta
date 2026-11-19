from django.forms import ( 
	ModelForm,  CharField, ValidationError
)
from django.forms.widgets import HiddenInput
from .models import Image
from .utils import base64_to_image
import uuid

class ImageForm(ModelForm):
	class Meta:
		model = Image		
		exclude = ('code', 'is_cover',)
		widgets = {
			'object_id': HiddenInput,
			'content_type': HiddenInput,
		}

class CoverImageForm(ModelForm):
	class Meta:
		model = Image		
		exclude = ('code', 'img', 'is_cover', 'object_id', 'content_type')		

	base64image = CharField(widget = HiddenInput, required=False)

	def clean_base64image(self):
		base64image = self.cleaned_data['base64image']
		if base64image:
			# Valida contenido, formato y tamaño; guarda el resultado para save().
			self._decoded_image = base64_to_image(base64image)
		return base64image

	def save(self, commit=True):
		base64image = self.cleaned_data['base64image']
		if not base64image:
			return
		if self.instance.id is not None and self.instance.img:			
			self.instance.img.delete()
		
		obj = super().save(commit=False)
		obj.is_cover=True
	
		data, extension = self._decoded_image
		filename = '%s.%s' % (str(uuid.uuid4()), extension)
		obj.img.save(filename, data, save=commit)

		if commit:
			obj.save()            
		return obj
