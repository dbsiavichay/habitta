from django import forms
from django.contrib import admin
from django.db.models import Count, Prefetch, Q
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils.html import format_html
from unfold.admin import GenericTabularInline, ModelAdmin, TabularInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateFilter, RelatedDropdownFilter
from unfold.decorators import display
from unfold.widgets import UnfoldAdminCheckboxSelectMultipleWidget

from apps.logs.models import Log
from apps.multimedia.models import Image
from apps.project.admin_utils import image_preview, short_date, site_link, user_header
from apps.project.templatetags.habitta import KIND_LABELS
from apps.project.utils import get_active_icons_url

from .forms import SpecificationForm
from .models import Category, Group, GroupCategory, Property, Purpose, Specification

KIND_BADGE = {Category.REAL_STATE: 'primary', Category.SERVICE: 'info', Category.JOB: 'warning'}


def kind_badge(kind):
    return kind, KIND_LABELS.get(kind, '—')


class IconStylesMixin:
    """Carga en la pantalla el CSS de los íconos: categorías (`fc-*`) y/o especificaciones (`lb-*`)."""

    icon_styles = ()

    @property
    def media(self):
        media = super().media
        urls = []
        if 'categories' in self.icon_styles:
            urls.append(static('plugins/fontcategories/fontcategories.css'))
        if 'specifications' in self.icon_styles and (url := get_active_icons_url()):
            urls.append(url)
        return media + forms.Media(css={'all': urls}) if urls else media


def icon_and_text(css_class, icon, text):
    if not icon:
        return format_html('<span class="flex items-center gap-2"><span style="width:20px"></span>{}</span>', text)
    return format_html(
        '<span class="flex items-center gap-2"><i class="{}-{}" style="font-size:20px;width:20px" aria-hidden="true">'
        '</i>{}</span>', css_class, icon, text,
    )


# ---------- Publicaciones ----------

class PropertyImageInline(GenericTabularInline):
    """Fotos del anuncio (sólo consulta: se administran desde el asistente de publicación)."""

    model = Image
    fields = ('preview', 'role')
    readonly_fields = fields
    extra = 0
    can_delete = False
    tab = True
    verbose_name = 'foto'
    verbose_name_plural = 'Fotos'

    ROLES = {'thumbnail': 'Miniatura', 'map': 'Mapa estático'}

    def has_add_permission(self, request, obj=None):
        return False

    @display(description='Imagen')
    def preview(self, obj):
        return image_preview(obj.img, height=96)

    @display(description='Uso')
    def role(self, obj):
        return self.ROLES.get(obj.code) or ('Portada' if obj.is_cover else 'Galería')


@admin.register(Property)
class PropertyAdmin(ModelAdmin):
    list_display = ('listing', 'kind', 'owner', 'views', 'likes', 'published', 'public_link')
    list_select_related = ('category', 'user__profile')
    list_filter = (
        ('category__kind', ChoicesDropdownFilter),
        ('category', RelatedDropdownFilter),
        ('pub_date', RangeDateFilter),
    )
    list_filter_submit = True
    search_fields = ('title', 'description', 'address', 'user__email', 'user__first_name', 'user__last_name')
    ordering = ('-pub_date',)
    readonly_fields = ('owner_detail', 'category', 'purpose', 'pub_date', 'map_link', 'specifications')
    fieldsets = (
        ('Anuncio', {'classes': ['tab'], 'fields': ('title', 'description', 'category', 'purpose', 'owner_detail', 'pub_date')}),
        ('Ubicación', {'classes': ['tab'], 'fields': ('address', 'radius', 'map_link')}),
        ('Especificaciones', {'classes': ['tab'], 'fields': ('specifications',)}),
    )
    inlines = [PropertyImageInline]
    warn_unsaved_form = True

    def has_add_permission(self, request):
        # Los anuncios se crean desde el asistente del sitio (categoría, especificaciones, fotos y mapa).
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            views_count=Count('log', filter=Q(log__type=Log.VIEW), distinct=True),
            likes_count=Count('log', filter=Q(log__type=Log.LIKE), distinct=True),
        ).prefetch_related(
            Prefetch('images', queryset=Image.objects.filter(code='thumbnail').order_by('pk'), to_attr='thumbnails'),
        )

    @display(description='Publicación', header=True, ordering='title')
    def listing(self, obj):
        thumbnails = [image for image in getattr(obj, 'thumbnails', []) if image.img]
        path = thumbnails[-1].img.url if thumbnails else static('brand/placeholder.svg')
        return [obj.title, obj.category.name, None, {'path': path, 'squared': True}]

    @display(description='Tipo', label=KIND_BADGE, ordering='category__kind')
    def kind(self, obj):
        return kind_badge(obj.category.kind)

    @display(description='Propietario', header=True, ordering='user__first_name')
    def owner(self, obj):
        return user_header(obj.user)

    @display(description='Vistas', ordering='views_count')
    def views(self, obj):
        return obj.views_count

    @display(description='Me gusta', ordering='likes_count')
    def likes(self, obj):
        return obj.likes_count

    @display(description='Publicado', ordering='pub_date')
    def published(self, obj):
        return short_date(obj.pub_date)

    @display(description='')
    def public_link(self, obj):
        return site_link(obj, 'Ver')

    @display(description='Propietario')
    def owner_detail(self, obj):
        user = obj.user
        return format_html('{} · <a href="mailto:{}" class="text-primary-600 dark:text-primary-500">{}</a>',
                           user.get_full_name() or user.get_username(), user.email, user.email)

    @display(description='Propósito')
    def purpose(self, obj):
        purpose = obj.get_purpose()
        return getattr(purpose, 'for_owner', None) or 'No definido'

    @display(description='Mapa')
    def map_link(self, obj):
        if not obj.geopoint:
            return 'Sin ubicación'
        # format_html escapa los argumentos (los vuelve texto): las coordenadas se formatean antes.
        lat, lng = f'{obj.geopoint.y:.6f}', f'{obj.geopoint.x:.6f}'
        return format_html(
            '<a href="https://www.openstreetmap.org/?mlat={0}&mlon={1}#map=17/{0}/{1}" target="_blank" rel="noopener" '
            'class="inline-flex items-center gap-1 font-medium text-primary-600 dark:text-primary-500">'
            '<span class="material-symbols-outlined">map</span>Ver en el mapa ({0}, {1})</a>',
            lat, lng,
        )

    @display(description='Especificaciones')
    def specifications(self, obj):
        try:
            specs = obj.get_specifications2()
        except (AttributeError, KeyError, TypeError):
            specs = []
        if not specs:
            return 'Sin especificaciones'
        rows = [[spec['group'], spec['key'], self._spec_value(spec)] for spec in specs]
        return render_to_string('unfold/components/table.html', {
            'table': {'headers': ['Grupo', 'Especificación', 'Valor'], 'rows': rows}, 'striped': 1,
        })

    @staticmethod
    def _spec_value(spec):
        if spec['downloadable']:
            return 'Archivo descargable (de pago)'
        value = spec['value']
        if value in (True, 'True'):
            return 'Sí'
        if value in (False, 'False'):
            return 'No'
        return value


# ---------- Catálogo ----------

class GroupCategoryInline(TabularInline):
    model = GroupCategory
    fields = ('group', 'sequence')
    extra = 0
    ordering = ('sequence',)
    ordering_field = 'sequence'
    hide_ordering_field = True
    tab = True
    verbose_name = 'formulario'
    verbose_name_plural = 'Formularios'


@admin.register(Category)
class CategoryAdmin(IconStylesMixin, ModelAdmin):
    icon_styles = ('categories',)
    list_display = ('category', 'kind_label', 'enabled', 'require_location', 'order', 'listings')
    list_filter = (('kind', ChoicesDropdownFilter), 'enabled', 'require_location')
    search_fields = ('name', 'singular_name')
    fieldsets = (
        ('Datos', {'classes': ['tab'], 'fields': ('kind', 'name', 'singular_name', 'icon', 'enabled', 'order')}),
        ('Publicación', {'classes': ['tab'], 'fields': ('require_location', 'is_salable', 'purposes', 'price_area', 'for_card')}),
    )
    inlines = [GroupCategoryInline]
    warn_unsaved_form = True

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(listings_count=Count('property', distinct=True))

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'purposes':
            kwargs['widget'] = UnfoldAdminCheckboxSelectMultipleWidget
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    @display(description='Categoría', ordering='name')
    def category(self, obj):
        return icon_and_text('fc', obj.icon, obj.name)

    # No se llama `kind`: con el mismo nombre que el campo, Django mostraría el campo y no la insignia.
    @display(description='Tipo', label=KIND_BADGE, ordering='kind')
    def kind_label(self, obj):
        return kind_badge(obj.kind)

    @display(description='Publicaciones', ordering='listings_count')
    def listings(self, obj):
        return obj.listings_count


@admin.register(Group)
class GroupAdmin(ModelAdmin):
    list_display = ('name', 'internal_name', 'columns', 'specs', 'categories')
    search_fields = ('name', 'internal_name', 'specifications__name')
    fields = ('name', 'internal_name', 'columns', 'specifications')
    filter_horizontal = ('specifications',)
    warn_unsaved_form = True

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            specs_count=Count('specifications', distinct=True),
            categories_count=Count('groupcategory', distinct=True),
        ).order_by('name')

    @display(description='Especificaciones', ordering='specs_count')
    def specs(self, obj):
        return obj.specs_count

    @display(description='Categorías que lo usan', ordering='categories_count')
    def categories(self, obj):
        return obj.categories_count


SPEC_TYPE_BADGE = {
    'CharField': 'info', 'IntegerField': 'primary', 'DecimalField': 'primary', 'BooleanField': 'success',
    'ChoiceField': 'warning', 'ChoiceField:RadioSelect': 'warning', 'FileField': 'danger',
}


@admin.register(Specification)
class SpecificationAdmin(IconStylesMixin, ModelAdmin):
    icon_styles = ('specifications',)
    form = SpecificationForm
    list_display = ('specification', 'internal_name', 'field_type_badge', 'is_required')
    list_filter = (('field_type', ChoicesDropdownFilter), 'is_required')
    search_fields = ('name', 'internal_name')
    fieldsets = (
        (None, {'fields': ('name', 'internal_name', 'icon')}),
        ('Campo en el formulario de publicación', {'fields': ('field_type', 'choices', 'attributes', 'is_required')}),
    )
    # "Elecciones" sólo aplica a los selectores (Selector y RadioMultiple).
    conditional_fields = {'choices': "field_type && field_type.startsWith('ChoiceField')"}
    warn_unsaved_form = True

    def get_form(self, request, obj=None, **kwargs):
        kwargs['help_texts'] = {
            'internal_name': 'Identificador único que usa el sistema (p. ej. «precio»). No lo cambies si ya hay anuncios.',
            'choices': 'Opciones separadas por coma. Ejemplo: Nuevo, Usado, Para remodelar.',
            'attributes': 'Atributos del campo separados por coma. Ejemplo: min=0, max=2030.',
            'icon': 'Ícono de la fuente activa (Contenido del sitio → Íconos).',
            **(kwargs.get('help_texts') or {}),
        }
        return super().get_form(request, obj, **kwargs)

    @display(description='Especificación', ordering='name')
    def specification(self, obj):
        return icon_and_text('lb', obj.icon, obj.name)

    @display(description='Tipo de campo', label=SPEC_TYPE_BADGE, ordering='field_type')
    def field_type_badge(self, obj):
        return obj.field_type, obj.get_field_type_display()


@admin.register(Purpose)
class PurposeAdmin(ModelAdmin):
    list_display = ('for_owner', 'for_user', 'activity', 'participle')
    ordering_field = 'order'
    hide_ordering_field = True
    fields = ('for_owner', 'for_user', 'activity', 'participle')
