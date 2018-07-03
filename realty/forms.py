from django.forms import ( 
	ModelForm, Form, 
	CheckboxSelectMultiple, ModelChoiceField, ModelMultipleChoiceField, 
	CharField, FloatField, ChoiceField
)
from django.forms.widgets import (
	TextInput, NumberInput,
	Select, RadioSelect
)
from .models import Category, Property
from django.contrib.gis.geos import Point

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
		place = super().save(commit=False)
		place.geopoint = Point(self.cleaned_data['longitude'], self.cleaned_data['latitude'])
		if commit:
			place.save()            
		return place


class PropertyDetailsForm(Form):
	def __init__(self, *args, **kwargs):
		category = kwargs.pop('category', None)
		instance = kwargs.pop('instance', None)		
		super().__init__(*args, **kwargs)

		if category is None and instance is None: 
			raise ValueError('Debe indicar una categoria o instancia')

		if category and not isinstance(category, Category):
			raise ValueError('Debe indicar una instancia de Category')

		if instance and not isinstance(instance, Property):
			raise ValueError('Debe indicar una instancia de Property')			

		if category is None and instance is not None:
			category = instance.category

		INPUT_WIDGETS = ('TextInput', 'NumberInput')
		CHOICE_WIDGETS = ('Select', 'RadioSelect')

		print(instance.id)

		p = Property.objects.get(pk=instance.id)
		print(p.details)
		print(instance.details)
		initials = instance.details['specifications'] if instance else {}
		print(initials)

		for specification in category.specifications.all():
			key = str(specification.id)
			initial = initials[key] if key in initials else None

			if specification.widget in INPUT_WIDGETS:
				self.fields[key] = CharField(
					label = specification.name,
					widget = eval(specification.widget),								
					required = specification.is_required,
					initial = initial
				)			
			elif specification.widget in CHOICE_WIDGETS:
				CHOICES = [(choice, choice) for choice in specification.choices.split(',')]				
				self.fields[key] = ChoiceField(
					label = specification.name,
					choices = CHOICES,
					widget = eval(specification.widget),					
					required = specification.is_required,
					initial = initial
				)							
			elif specification.widget == 'checkbox':
				self.fields[key] = BooleanField(
					label = specification.name,
					initial = initial	
				)
			else:
				pass