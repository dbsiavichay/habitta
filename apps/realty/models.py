from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.contrib.gis.db import models
from django.db.models import Q
from django.urls import reverse_lazy
from django.template.loader import render_to_string
from apps.multimedia.mixins import ImageMixin

from .utils import get_category_icons, get_larbit_icons

from fontawesome.fields import IconField

#Lo que se pretende hacer con la propiedad ej: vender, rentar
class Purpose(models.Model):
    class Meta:
        verbose_name = 'propósito'
        ordering = ['order',]

    for_owner = models.CharField(max_length=32, verbose_name='para el propietario') 
    for_user = models.CharField(max_length=32, verbose_name='para el usuario')      
    activity = models.CharField(max_length=32, verbose_name='actividad')
    participle = models.CharField(max_length=32, verbose_name='participio')
    order = models.PositiveSmallIntegerField(default=1, verbose_name='orden')

    def __str__(self):
        return self.for_owner

class Specification(models.Model):
    ICON_CHOICES = get_larbit_icons()

    FIELD_CHOICES = (       
        ('CharField', 'Texto'),('IntegerField', 'Número Entero'), ('DecimalField', 'Número decimal'),
        ('BooleanField', 'Booleano'), ('ChoiceField', 'Selector'), ('ChoiceField:RadioSelect', 'RadioMultiple'), 
        ('FileField', 'Archivo'),
    )   
    
    name = models.CharField(max_length=128, verbose_name='nombre')
    internal_name = models.CharField(max_length=128, unique=True, verbose_name='nombre interno')
    field_type = models.CharField(max_length=64, choices=FIELD_CHOICES, verbose_name='tipo de campo')
    attributes = models.CharField(max_length=128, blank=True, null=True, verbose_name='atributos')
    choices = models.CharField(max_length=256, blank=True, null=True, verbose_name='elecciones')    
    icon = models.CharField(max_length=32, blank=True, null=True, choices=ICON_CHOICES, verbose_name='ícono')
    is_required = models.BooleanField(default=False, verbose_name='requerido?') 

    def __str__(self):
        return self.name
        
    class Meta:
        verbose_name = 'especificación'
        verbose_name_plural = 'especificaciones'
        ordering = ['name',]

class Group(models.Model):
    COLUMNS_CHOICES = (('col-xs-12', '1'),('col-xs-6', '2'),('col-xs-4', '3'))

    name = models.CharField(max_length=32, verbose_name='nombre')
    internal_name = models.CharField(max_length=64, verbose_name='nombre de uso interno')   
    columns = models.CharField(max_length=16, choices=COLUMNS_CHOICES, default='col-xs-12', verbose_name='número de columnas')    
    specifications = models.ManyToManyField(Specification, verbose_name='especifaciones para este grupo')

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'formulario'

class Category(models.Model):   
    ICON_CHOICES = get_category_icons()

    REAL_STATE, SERVICE, JOB = (1, 2, 3)
    KIND_CHOICES = (
        (REAL_STATE, 'Inmobiliario'), (SERVICE, 'Servicio'), (JOB, 'Empleo')
    )
    
    kind = models.PositiveSmallIntegerField(choices=KIND_CHOICES, verbose_name='tipo')
    name = models.CharField(max_length=64, verbose_name='nombre', unique=True)
    singular_name = models.CharField(max_length=64, verbose_name='nombre singular')
    price_area = models.CharField(max_length=64, blank=True, null=True, verbose_name='área del precio') 
    enabled = models.BooleanField(default=True, verbose_name='habilitado?')
    icon = models.CharField(max_length=32, blank=True, null=True, choices=ICON_CHOICES, verbose_name='icono')
    order = models.PositiveSmallIntegerField(verbose_name='orden')  
    require_location = models.BooleanField(default=True, verbose_name='requiere ubicación?')
    is_salable = models.BooleanField(default=False, verbose_name='puede venderse?')
    purposes = models.ManyToManyField(Purpose, blank=True, verbose_name='propósitos')
    for_card = models.CharField(max_length=128, blank=True, null=True, verbose_name="especificaciones aplicables en tarjeta", help_text="Si es más de uno separe por coma")
    groups = models.ManyToManyField(Group, through='GroupCategory', blank=True, verbose_name='grupos de especificaciones')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'categoría'
        ordering = ('kind', 'name',)

class GroupCategory(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, verbose_name='formulario')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name='categoría')    
    sequence = models.PositiveSmallIntegerField(verbose_name='secuencia')

    class Meta:
        verbose_name = 'formulario de categoría'
        verbose_name_plural = 'formularios de categoría'

class Property(ImageMixin, models.Model):
    class Meta:
        verbose_name = 'propiedad'
        verbose_name_plural = 'propiedades'
        ordering = ['-pub_date',]

    DRAFT, PUBLISHED, COMPLETE = (1, 2, 3)

    STATUS_CHOICES = (
        (DRAFT, 'Borrador'), (PUBLISHED, 'Publicado'), (COMPLETE, 'Completado'),
    )

    title = models.CharField(max_length=32, verbose_name='descripción rápida (Max 32 caracteres)')
    description = models.TextField(blank=True, null=True, verbose_name='descripción')
    address = models.CharField(max_length=64, blank=True, null=True, verbose_name='dirección')
    geopoint = models.PointField(blank=True, null=True) 
    status = models.PositiveSmallIntegerField(default=DRAFT)
    details = JSONField(blank=True, null=True, verbose_name='detalles') 
    pub_date = models.DateTimeField(auto_now_add=True, verbose_name='fecha de publicación') 
    category = models.ForeignKey(Category, verbose_name='categoría', on_delete=models.CASCADE)  
    user = models.ForeignKey('auth.User', verbose_name='propietario', on_delete=models.CASCADE)

    def __str__(self):
        return self.title or self.description

    def get_price_area(self):
        try:
            specification = Specification.objects.get(internal_name__iexact=self.category.price_area)
            key = str(specification.id)
            r = self.details['specifications'][key] if key in self.details['specifications'] else self.category.price_area
            r = float(r)
        except:
            r = self.category.price_area

        return r

    def get_purpose(self):
        try:
            pk = self.details['purpose']
            purpose = Purpose.objects.get(pk=pk)
            return purpose      
        except:
            return {'activity': 'No definido'}

    def get_specifications_for_card(self):
        specifications = []
        if not self.category.for_card: return specifications
        names = [name.strip() for name in self.category.for_card.split(',')]
        params = Q()
        for name in names:
            params = params | Q(internal_name__iexact=name)
        for spc in Specification.objects.filter(params):
            key = str(spc.id)
            if len(specifications) == 2: break
            if key in self.details['specifications'] and not 'FileField' in spc.field_type:
                item = {
                    'key': spc.name,
                    'value': self.details['specifications'][key],
                    'icon': spc.icon,
                }
                specifications.append(item)
        return specifications


    def get_specifications(self):
        specifications = []

        for spc in self.category.specifications.all():
            key = str(spc.id)
            if key in self.details['specifications']:
                specifications.append({
                    'key': spc.name,
                    'value': self.details['specifications'][key],
                    'icon': spc.icon,
                    'require_payment': True if 'FileField' in spc.field_type else False
                })
        return specifications

    def get_specifications2(self):
        specifications = []

        for group in self.category.groups.all().order_by('groupcategory__sequence'):            
            for spc in group.specifications.all():
                key = str(spc.id)
                if key in self.details['specifications']:
                    specifications.append({
                        'key': spc.name,
                        'value': self.details['specifications'][key],
                        'icon': spc.icon,
                        'downloadable': True if 'FileField' in spc.field_type else False,
                        'group': group.name
                    })
        return specifications

    def get_path_files(self):
        files = []
        specifications = Specification.objects.filter(group__category=self.category)
        for spc in specifications:
            key = str(spc.id)
            if 'FileField' in spc.field_type and key in self.details['specifications']:
                files.append(self.details['specifications'][key])
        return files

    def render_list_card(self):
        template_name = 'realty/property_card.html'
        rendered = render_to_string(template_name, context={'object':self})
        return rendered

    def get_absolute_url(self):     
        return reverse_lazy('detail_property', args=[str(self.id)])

    def get_thumbnail(self):
        image = self.get_last_image_by_code('thumbnail')
        if image and image.img:
            return image.img.url

        return settings.STATIC_URL + 'images/bg/1.png'

    #Usado para el serializer en api
    def get_longitude(self):
        return self.geopoint.x if self.category.require_location else 0
    
    def get_latitude(self):
        return self.geopoint.y if self.category.require_location else 0


