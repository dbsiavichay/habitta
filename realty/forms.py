from django.forms import ModelForm, CheckboxSelectMultiple
from .models import Property

class PropertyForm(ModelForm):
    class Meta:
        model = Property
        fields = '__all__'
        widgets = {
        	'services':CheckboxSelectMultiple,
        }