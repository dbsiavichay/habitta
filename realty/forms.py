from django.forms import ModelForm, CheckboxSelectMultiple, ModelMultipleChoiceField, FloatField
from .models import Property
from django.contrib.gis.geos import Point

class PropertyForm(ModelForm):
	longitude = FloatField(label='Longitud')
	latitude = FloatField(label='Latitud')
	services = ModelMultipleChoiceField(
		widget = CheckboxSelectMultiple,
		queryset = None
	)

	class Meta:
		model = Property
		exclude = ('user', 'geopoint')        

	def __init__(self, *args, **kwargs):		
		category = kwargs.pop('category', None)
		super().__init__(*args, **kwargs)
		self.fields['services'].queryset = category.services 
		if self.instance.geopoint is not None:
			self.fields['longitude'].initial = self.instance.geopoint.x
			self.fields['latitude'].initial = self.instance.geopoint.y 

	def save(self, commit=True):
		place = super().save(commit=False)
		place.geopoint = Point(self.cleaned_data['longitude'], self.cleaned_data['latitude'])
		if commit:
			place.save()            
		return place   	