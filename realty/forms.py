from django.forms import ( 
	ModelForm, Form, 
	ModelChoiceField, ModelMultipleChoiceField, 
	CharField, IntegerField,FloatField, ChoiceField, BooleanField, FileField,
	ValidationError
)
from django.forms.widgets import (
	TextInput, NumberInput, HiddenInput,
	Select, RadioSelect,
	CheckboxSelectMultiple
)
from .models import Specification, Category, Purpose, Property
from django.contrib.gis.geos import Point

from django.core.files.storage import FileSystemStorage
import os
import uuid

#Custom form fields
class PurposeChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.for_user

class SpecificationMultipleChoiceField(ModelMultipleChoiceField):
	def label_from_instance(self, obj):
		return obj.internal_name
#####

class CategoryForm(ModelForm):
	specifications = SpecificationMultipleChoiceField(
		queryset = Specification.objects.all(),
		label = 'Especificaciones',
		widget = CheckboxSelectMultiple,
		required = False,
	)

	class Meta:
		model = Category
		fields = '__all__'
		widgets = {
			'purposes': CheckboxSelectMultiple,
			'services': CheckboxSelectMultiple,			
		}

class SpecificationForm(ModelForm):
	class Meta:
		model = Specification
		fields = '__all__'		

	def clean(self):
		super().clean()
		field_type = self.cleaned_data.get('field_type')
		choices = self.cleaned_data.get('choices')
		

		if field_type and 'ChoiceField' in field_type  and choices is None:            
			raise ValidationError(
				'Si selecciona un widget de tipo %(field_type)s debe completar las elecciones',
				code = 'invalid',
				params = {'field_type': field_type}                
			)           

		return self.cleaned_data

class PropertyForm(ModelForm):
	longitude = FloatField(widget=HiddenInput)
	latitude = FloatField(widget=HiddenInput)
	purpose = ModelChoiceField(
		label = '¿Que desea hacer?',
		empty_label = None,
		widget = RadioSelect,
		queryset = None,
		required = True,

	)
	services = ModelMultipleChoiceField(
		widget = CheckboxSelectMultiple,
		queryset = None,
		required = False
	)

	class Meta:
		model = Property
		exclude = ('user', 'geopoint', 'status', 'category')		

	def __init__(self, *args, **kwargs):		
		self.category = kwargs.pop('category', None)
		super().__init__(*args, **kwargs)						
		if self.category is not None:
			purposes = self.category.purposes
			services = self.category.services

		self.fields['purpose'].queryset = purposes		 
		self.fields['services'].queryset = services		

		if self.instance.pk:
			try:
				self.fields['purpose'].initial = self.instance.details['purpose']
			except KeyError:
				pass
			try:
				self.fields['services'].initial = self.instance.details['services']
			except KeyError:
				pass

		if not self.category.require_location:
			self.fields['longitude'].required = False
			self.fields['latitude'].required = False

		if self.instance.geopoint is not None:
			self.fields['longitude'].initial = self.instance.geopoint.x
			self.fields['latitude'].initial = self.instance.geopoint.y 

		#self.fields['purpose'].choices = ((obj.id, obj) for obj in self.fields['purpose'].choices.queryset)		

	def save(self, commit=True):
		property = super().save(commit=False)
		if self.category.require_location:		
			property.geopoint = Point(self.cleaned_data['longitude'], self.cleaned_data['latitude'])
		if commit:
			property.save()            
		return property


class PropertyDetailsForm(Form):
	def __init__(self, *args, **kwargs):
		self.category = kwargs.pop('category', None)		
		super().__init__(*args, **kwargs)

		if self.category is None or not isinstance(self.category, Category): 
			raise ValueError('Debe indicar una categoria')

		for specification in self.category.specifications.all():
			key = str(specification.id)
			try:
				form_field, widget = specification.field_type.split(':')
			except ValueError:
				form_field = specification.field_type
				widget = None			

			self.fields[key] = eval(form_field)(
				label = specification.name,
				required = specification.is_required,
			)
						
			if widget: self.fields[key].widget = eval(widget)()
			if specification.choices:
				CHOICES = [(choice, choice) for choice in specification.choices.split(',')]
				self.fields[key].choices = CHOICES
			
			pairs = (pair.split('=') for pair in specification.attributes.split(',')) if specification.attributes is not None else None			
			attrs = dict((key.strip(), eval(value.strip())) for key, value in pairs) if pairs is not None else {}
			self.fields[key].widget.attrs.update(attrs)

	def get_not_empty_cleaned_data(self):
		import time
		if not self.cleaned_data:
			return []
		not_empty_cleaned_data = { key:self.cleaned_data[key] for key in self.cleaned_data if self.cleaned_data[key] }

		for specification in self.category.specifications.all():
			key = str(specification.id)
			if 'FileField' in specification.field_type:
				uploaded_file = self.cleaned_data[key]
				name, extension = os.path.splitext(uploaded_file.name)
				fs = FileSystemStorage(location='media/files/%s/'% (time.strftime('%Y/%m/%d')))
				filename = '%s%s' % (str(uuid.uuid4()),extension)
				file = fs.save(filename, uploaded_file)
				file_path = fs.path(file)
				not_empty_cleaned_data[key] = file_path

		return not_empty_cleaned_data

class FinderForm(Form):
	purpose = PurposeChoiceField(
		queryset = Purpose.objects.all(),
		empty_label = '¿Que deseas hacer?',
		required = False
	)
	category = ModelChoiceField(
		queryset = Category.objects.all(),
		empty_label = 'Todas las categorías',		
		required = False
	)
	address = CharField(required=False)
