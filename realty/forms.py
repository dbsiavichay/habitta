from django.forms import ( 
	ModelForm, Form, 
	CheckboxSelectMultiple, ModelChoiceField, ModelMultipleChoiceField, 
	CharField, FloatField, ChoiceField
)
from django.forms.widgets import RadioSelect, NumberInput
from .models import Property
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
		super().__init__(*args, **kwargs)		

		for specification in category.specifications.all():
			key = str(specification.id)			
		
			if specification.widget == 'number':
				self.fields[key] = CharField(
					label = specification.name,
					widget = NumberInput,								
					required = specification.is_required
				)
			elif specification.widget == 'text':
				self.fields[key] = CharField(
					label = specification.name,										
					required = specification.is_required
				)
			elif specification.widget == 'select':
				CHOICES = [(choice, choice) for choice in specification.choices.split(',')]
				CHOICES = [('', '---------')] + CHOICES
				self.fields[key] = ChoiceField(
					label = specification.name,
					choices = CHOICES,					
					required = specification.is_required					
				)				
			elif specification.widget == 'radio':
				CHOICES = [(choice, choice) for choice in specification.choices.split(',')]
				self.fields[key] = ChoiceField(
					label = specification.name,
					widget = RadioSelect,
					choices = CHOICES,					
					required = specification.is_required
				)
			elif specification.widget == 'checkbox':
				self.fields[key] = BooleanField(
					label = specification.name,	
				)
			else:
				pass