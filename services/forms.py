from django.forms import ModelForm, FloatField
from django.forms.widgets import HiddenInput
from django.contrib.gis.geos import Point
from .models import Service

class ServiceForm(ModelForm):
	longitude = FloatField(widget=HiddenInput)
	latitude = FloatField(widget=HiddenInput)

	class Meta:
		model = Service
		exclude = ['user', 'geopoint']

	def save(self, commit=True):
		obj = super().save(commit=False)			
		obj.geopoint = Point(self.cleaned_data['longitude'], self.cleaned_data['latitude'])
		if commit:
			obj.save()            
		return obj