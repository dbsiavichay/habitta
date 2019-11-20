from django.core.validators import FileExtensionValidator
from django.forms import ( 
    ModelForm, Form, 
    ModelChoiceField, ModelMultipleChoiceField, 
    CharField, IntegerField, DecimalField, FloatField, ChoiceField, BooleanField, FileField,
    ValidationError
)
from django.forms.widgets import (
    TextInput, NumberInput, HiddenInput,
    Select, RadioSelect,
    CheckboxSelectMultiple
)

from .widgets import ColumnCheckboxSelectMultiple

from .models import Specification, Group, Category, Purpose, Property
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

class GroupForm(ModelForm):
    class Meta:
        model = Group
        fields = '__all__'
        widgets = {
            'specifications': ColumnCheckboxSelectMultiple(columns=4, css_class='col-md-3', wrapper_css_class='row',)           
        }

class CategoryForm(ModelForm):
    class Meta:
        model = Category
        fields = '__all__'
        widgets = {
            'purposes': CheckboxSelectMultiple,
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
    class Meta:
        model = Property
        fields = ('category', 'title', 'description',)

# class PropertyForm(ModelForm):    
#   purpose = ModelChoiceField(
#       label = '¿Que desea hacer?',
#       empty_label = None,
#       widget = RadioSelect,
#       queryset = Purpose.objects.none(),
#       required = True,

#   )

#   class Meta:
#       model = Property
#       fields = ('category', 'purpose', 'title', 'description',)       

#   def __init__(self, *args, **kwargs):        
#       self.category = kwargs.pop('category', None)
#       self.kind = kwargs.pop('kind', None)
#       super().__init__(*args, **kwargs)                       
#       if self.kind and self.kind == Category.SERVICE:
#           queryset = self.fields['category'].queryset.filter(kind=self.kind)
#           self.fields['category'].queryset = queryset
#           purposes = Category.objects.filter(kind=self.kind).last().purposes.all()
#           self.fields['purpose'].widget = HiddenInput()
#           self.fields['purpose'].queryset = purposes
#           self.fields['purpose'].initial = purposes[0]

#       else:
#           purposes = self.category.purposes.all()
#           if len(purposes) == 1:
#               self.fields['purpose'].widget = HiddenInput()
#               self.fields['purpose'].initial = purposes[0]
#           self.fields['purpose'].queryset = purposes          
#           self.fields['category'].initial = self.category
#           self.fields['category'].widget = HiddenInput()


#       if self.instance.pk:
#           try:
#               self.fields['purpose'].initial = self.instance.details['purpose']
#           except KeyError:
#               pass

class LocationForm(Form):
    longitude = FloatField(widget=HiddenInput)
    latitude = FloatField(widget=HiddenInput)
    address = CharField(max_length=64, label='Dirección')

    def get_geopoint(self):
        geopoint = Point(self.cleaned_data['longitude'], self.cleaned_data['latitude'])     
        return geopoint 


class GroupDetailsForm(Form):
    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop('group')        
        super().__init__(*args, **kwargs)

        if not self.group or not isinstance(self.group, Group): 
            raise ValueError('Debe indicar una grupo.')

        self.generate_fields()

    def generate_fields(self):
        for specification in self.group.specifications.all():
            key = str(specification.id)
            try:
                form_field, widget = specification.field_type.split(':')
            except ValueError:
                form_field = specification.field_type
                widget = None           

            self.fields[key] = eval(form_field)(
                label = specification.name,
                required = specification.is_required,
                validators = [FileExtensionValidator(allowed_extensions=['pdf', 'dwg'])] if form_field == 'FileField' else []
            )
                        
            if widget: self.fields[key].widget = eval(widget)()
            if specification.choices:
                CHOICES = [(choice.strip(), choice.strip()) for choice in specification.choices.split(',')]
                self.fields[key].choices = CHOICES
            
            pairs = (pair.split('=') for pair in specification.attributes.split(',')) if specification.attributes is not None else None         
            attrs = dict((key.strip(), eval(value.strip())) for key, value in pairs) if pairs is not None else {}
            self.fields[key].widget.attrs.update(attrs)
            self.calculate_columns()

    def calculate_columns(self):
        cols = 2
        width = 12 // cols

        min = 0
        results = []
        for i in range(len(self.visible_fields()) // cols):
            results.append((f"{min}:{min+cols}", width))
            min += cols
        
        if len(self.visible_fields()) % cols:
            results.append((f"{min}:", width))
        
        self.columns = results



    def get_not_empty_cleaned_data(self):
        import time
        if not self.cleaned_data:
            return []
        not_empty_cleaned_data = { key:str(self.cleaned_data[key]) for key in self.cleaned_data if self.cleaned_data[key] }

        for specification in self.group.specifications.all():
            key = str(specification.id)
            if 'FileField' in specification.field_type and self.cleaned_data[key]:
                uploaded_file = self.cleaned_data[key]
                name, extension = os.path.splitext(uploaded_file.name)
                fs = FileSystemStorage(location='media/files/%s/'% (time.strftime('%Y/%m/%d')))
                filename = '%s%s' % (str(uuid.uuid4()),extension)
                file = fs.save(filename, uploaded_file)
                file_path = fs.path(file)
                not_empty_cleaned_data[key] = file_path

        return not_empty_cleaned_data

class FinderForm(Form):
    search_purpose = PurposeChoiceField(
        queryset = Purpose.objects.all(),
        empty_label = '¿Que deseas hacer?',
        required = False
    )
    search_category = ModelChoiceField(
        queryset = Category.objects.all(),
        empty_label = 'Todas las categorías',       
        required = False
    )
    search_address = CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'search_purpose' in self.initial:
            queryset = self.fields['search_category'].queryset
            self.fields['search_category'].queryset = queryset.filter(purposes=self.initial['search_purpose'])

