from django.forms import ( 
	ModelForm, Form, 
	ModelChoiceField, ModelMultipleChoiceField, 
	CharField, FloatField, ChoiceField, BooleanField,
	ValidationError
)
from django.forms.widgets import (
	TextInput, NumberInput, HiddenInput,
	Select, RadioSelect,
	CheckboxSelectMultiple
)
from .models import Specification, Category, Purpose, Property, PropertyImage
from django.contrib.gis.geos import Point

class SpecificationForm(ModelForm):
	class Meta:
		model = Specification
		fields = '__all__'

	def clean(self):
		super().clean()
		widget = self.cleaned_data.get('widget')
		choices = self.cleaned_data.get('choices')

		CHOICE_WIDGETS = ('Select', 'RadioSelect')

		if widget in CHOICE_WIDGETS  and choices is None:            
			raise ValidationError(
				'Si selecciona un widget de tipo %(widget)s debe completar las elecciones',
				code = 'invalid',
				params = {'widget': widget}                
			)           

		return self.cleaned_data

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

		INPUT_WIDGETS = ('TextInput', 'NumberInput',)
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
				CHOICES = [(choice, choice) for choice in specification.choices.split(',')] if specification.choices is not None else []
				self.fields[key] = ChoiceField(
					label = specification.name,
					choices = CHOICES,
					widget = eval(specification.widget),					
					required = specification.is_required,					
				)							
			elif specification.widget == 'CheckboxInput':
				self.fields[key] = BooleanField(
					label = specification.name,					
				)
			else:
				pass

class PropertyBase64ImageForm(ModelForm):
	class Meta:
		model = PropertyImage		
		fields = ('is_cover', 'property',)
		widgets = {				
			'is_cover': HiddenInput,
			'property': HiddenInput,
		}

	base64image = CharField(widget = HiddenInput,)	

	def save(self, commit=True):
		import uuid
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


class PurposeChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.for_user

class FinderForm(Form):
	address = CharField(required=False)
	category = ModelChoiceField(
		queryset = Category.objects.all(),
		empty_label = 'Todas las categorías',		
		required = False
	)
	purpose = PurposeChoiceField(
		queryset = Purpose.objects.all(),
		empty_label = '¿Que deseas hacer?',
		required = False
	)
