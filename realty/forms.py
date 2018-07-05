from django.forms import ( 
	ModelForm, Form, 
	CheckboxSelectMultiple, ModelChoiceField, ModelMultipleChoiceField, 
	CharField, FloatField, ChoiceField
)
from django.forms.widgets import (
	TextInput, NumberInput, HiddenInput,
	Select, RadioSelect
)
from .models import Category, Property, PropertyImage
from django.contrib.gis.geos import Point

import datetime as dt

class PropertyForm(ModelForm):
	longitude = FloatField(label='Longitud')
	latitude = FloatField(label='Latitud')
	services = ModelMultipleChoiceField(
		widget = CheckboxSelectMultiple,
		queryset = None,
		required = False
	)

	class Meta:
		model = Property
		exclude = ('user', 'geopoint', 'status', 'category')
		widgets = {
			'purpose': RadioSelect
		}

	def __init__(self, *args, **kwargs):		
		category = kwargs.pop('category', None)
		super().__init__(*args, **kwargs)				
		if self.instance.pk is not None:
			services = self.instance.category.services			
		elif category is not None:
			services = category.services

		self.fields['services'].queryset = services 		
		self.fields['services'].initial = self.instance.details['services'] if self.instance.pk else []
		if self.instance.geopoint is not None:
			self.fields['longitude'].initial = self.instance.geopoint.x
			self.fields['latitude'].initial = self.instance.geopoint.y 

		self.fields['purpose'].choices = ((obj.id, obj) for obj in self.fields['purpose'].choices.queryset)		

	def save(self, commit=True):
		property = super().save(commit=False)
		property.geopoint = Point(self.cleaned_data['longitude'], self.cleaned_data['latitude'])
		if commit:
			property.save()            
		return property


class PropertyDetailsForm(Form):
	def __init__(self, *args, **kwargs):
		category = kwargs.pop('category', None)		
		super().__init__(*args, **kwargs)

		if category is None or not isinstance(category, Category): 
			raise ValueError('Debe indicar una categoria')

		INPUT_WIDGETS = ('TextInput', 'NumberInput')
		CHOICE_WIDGETS = ('Select', 'RadioSelect')		

		for specification in category.specifications.all():
			key = str(specification.id)			

			if specification.widget in INPUT_WIDGETS:
				self.fields[key] = CharField(
					label = specification.name,
					widget = eval(specification.widget),								
					required = specification.is_required,
				)			
			elif specification.widget in CHOICE_WIDGETS:
				CHOICES = [(choice, choice) for choice in specification.choices.split(',')]				
				self.fields[key] = ChoiceField(
					label = specification.name,
					choices = CHOICES,
					widget = eval(specification.widget),					
					required = specification.is_required,					
				)							
			elif specification.widget == 'checkbox':
				self.fields[key] = BooleanField(
					label = specification.name,					
				)
			else:
				pass

class PropertyImageForm(ModelForm):
	class Meta:
		model = PropertyImage		
		fields = '__all__'
		widgets = {				
			'is_cover': HiddenInput,
			'property': HiddenInput,
		}	

class PropertyBase64ImageForm(PropertyImageForm):		
	base64image = CharField(widget = HiddenInput,)

	class Meta(PropertyImageForm.Meta):		
		fields = ('is_cover', 'property',)

	def save(self, commit=True):
		from .utils import base64_to_image

		base64image = self.cleaned_data['base64image']
		property = self.cleaned_data['property']
		today = dt.datetime.today().strftime("%Y%m%d%H%M%S")

		if self.instance.id is not None and self.instance.img:
			self.instance.img.delete()

		obj = super().save(commit=False)
	
		data, ext = base64_to_image(base64image)				
		file_name = 'cover-%s-%s.%s' % (property.id, today, ext)
		obj.img.save(file_name, data)

		if commit:
			obj.save()            
		return obj