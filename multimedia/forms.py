from django.forms import ( 
	ModelForm,  CharField, ValidationError
)
from django.forms.widgets import HiddenInput
from .models import Image
import uuid

class Base64ImageForm(ModelForm):
	class Meta:
		model = Image		
		exclude = ('img',)
		widgets = {				
			'is_cover': HiddenInput,
			'object_id': HiddenInput,
			'content_type': HiddenInput,
		}

	base64image = CharField(widget = HiddenInput,)	

	def save(self, commit=True):		
		from .utils import base64_to_image

		base64image = self.cleaned_data['base64image']			

		if self.instance.id is not None and self.instance.img:
			self.instance.img.delete()

		obj = super().save(commit=False)
	
		data, extension = base64_to_image(base64image)				
		filename = '%s.%s' % (str(uuid.uuid4()), extension)
		obj.img.save(filename, data)

		if commit:
			obj.save()            
		return obj
