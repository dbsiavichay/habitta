import ast
import logging

from django.conf import settings
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

logger = logging.getLogger(__name__)

# Tipos de campo y widgets permitidos para las especificaciones dinámicas
# (antes se resolvían con eval() sobre datos de la base de datos).
SPECIFICATION_FIELDS = {
    'CharField': CharField,
    'IntegerField': IntegerField,
    'DecimalField': DecimalField,
    'FloatField': FloatField,
    'BooleanField': BooleanField,
    'ChoiceField': ChoiceField,
    'FileField': FileField,
}
SPECIFICATION_WIDGETS = {
    'RadioSelect': RadioSelect,
    'Select': Select,
    'TextInput': TextInput,
    'NumberInput': NumberInput,
}


def parse_widget_attributes(attributes):
    """Convierte 'min=0, max=2020' en {'min': 0, 'max': 2020} sin ejecutar código."""
    attrs = {}
    if not attributes:
        return attrs
    for pair in attributes.split(','):
        name, sep, value = pair.partition('=')
        if not sep or not name.strip():
            continue
        value = value.strip()
        try:
            attrs[name.strip()] = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            attrs[name.strip()] = value
    return attrs

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
    """Datos básicos del anuncio. La categoría no viaja en el formulario: la fija la vista
    (URL al crear, el propio anuncio al editar)."""
    purpose = ModelChoiceField(
        label = '¿Qué quieres hacer?',
        empty_label = None,
        widget = RadioSelect,
        queryset = Purpose.objects.none(),
        required = True,
    )

    class Meta:
        model = Property
        fields = ('purpose', 'title', 'description',)
        labels = {
            'title': 'Título del anuncio',
            'description': 'Descripción',
        }
        help_texts = {
            'title': 'Corto y claro: qué es y dónde. Máximo 32 caracteres.',
        }

    def __init__(self, *args, **kwargs):
        self.category = kwargs.pop('category')
        super().__init__(*args, **kwargs)
        self.fields['title'].widget.attrs.update({'placeholder': 'Ej.: Casa con jardín en Cumbayá', 'autocomplete': 'off'})
        self.fields['description'].widget.attrs.update({
            'rows': 6, 'placeholder': 'Cuenta lo que hace especial tu anuncio: estado, entorno, condiciones…',
        })

        purposes = self.category.purposes.all()
        if len(purposes) == 1:
            self.fields['purpose'].widget = HiddenInput()
            self.fields['purpose'].initial = purposes[0]
        self.fields['purpose'].queryset = purposes

        if self.instance.pk:
            try:
                instance_purpose = int((self.instance.details or {})['purpose'])
            except (KeyError, TypeError, ValueError):
                instance_purpose = None

            if instance_purpose in purposes.values_list("id", flat=True):
                self.fields['purpose'].initial = instance_purpose
            elif len(purposes) == 1:
                self.fields['purpose'].initial = purposes[0]
            else:
                self.fields['purpose'].initial = None

class LocationForm(Form):
    longitude = FloatField(widget=HiddenInput)
    latitude = FloatField(widget=HiddenInput)
    address = CharField(max_length=255, label='Ciudad o zona donde trabajas')
    radius = IntegerField(min_value=1, label='Radio de operación (m)', initial=3000)

    def __init__(self, *args, **kwargs):
        require_location = kwargs.pop('require_location')
        super().__init__(*args, **kwargs)
        if require_location:
            # Con ubicación exacta no hay radio de operación: el campo va oculto en 0.
            self.fields['address'].label='Dirección'
            self.fields['radius'] = IntegerField(widget=HiddenInput(), required=False, min_value=0, initial=0)

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
            form_field, _, widget = specification.field_type.partition(':')
            field_class = SPECIFICATION_FIELDS.get(form_field)
            if field_class is None:
                logger.warning('Tipo de campo no permitido en especificación %s: %r', specification.pk, form_field)
                continue

            self.fields[key] = field_class(
                label=specification.name,
                required=specification.is_required,
                validators=[FileExtensionValidator(allowed_extensions=['pdf', 'dwg'])] if field_class is FileField else [],
            )

            if widget in SPECIFICATION_WIDGETS:
                self.fields[key].widget = SPECIFICATION_WIDGETS[widget]()
            if specification.choices:
                CHOICES = [(choice.strip(), choice.strip()) for choice in specification.choices.split(',')]
                # Un selector opcional necesita una opción vacía; si no, siempre se enviaba la primera
                if field_class is ChoiceField and not specification.is_required and not widget:
                    CHOICES = [('', 'Sin especificar')] + CHOICES
                self.fields[key].choices = CHOICES

            self.fields[key].widget.attrs.update(parse_widget_attributes(specification.attributes))
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
        if not self.cleaned_data and not self.files:
            return []
        not_empty_cleaned_data = { key:str(self.cleaned_data[key]) for key in self.cleaned_data if self.cleaned_data[key] }
        for specification in self.group.specifications.all():
            key = str(specification.id)
            if 'FileField' in specification.field_type and key in self.files and self.files[key]:
                uploaded_file = self.files[key]
                name, extension = os.path.splitext(uploaded_file.name)
                fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'files', time.strftime('%Y/%m/%d')))
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
        empty_label = '¿Que estás buscando?',       
        required = False
    )
    search_address = CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'search_purpose' in self.initial:
            queryset = self.fields['search_category'].queryset
            self.fields['search_category'].queryset = queryset.filter(purposes=self.initial['search_purpose'])

