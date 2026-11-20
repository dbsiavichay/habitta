from django.contrib import admin
from django.db.models import Max
from django.utils.text import Truncator
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import Settings, Icons, Term, Help

# Título de la barra superior en el inicio (por defecto "Sitio administrativo"). La marca, el menú
# y el dashboard se configuran en config/unfold.py.
admin.site.index_title = 'Inicio'

ACTIVE_LABEL = {'Activa': 'success'}


class SingleActiveAdmin(ModelAdmin):
	"""Sólo una fila puede estar activa: al activar una se desactivan las demás."""

	def save_model(self, request, obj, form, change):
		if obj.is_active:
			self.model.objects.all().update(is_active=False)
		super().save_model(request, obj, form, change)

	@display(description='Estado', label=ACTIVE_LABEL, ordering='is_active')
	def status(self, obj):
		return 'Activa' if obj.is_active else 'Inactiva'


@admin.register(Settings)
class SettingsAdmin(SingleActiveAdmin):
	list_display = ('settings', 'status')
	fieldsets = (
		('Fondos del sitio', {
			'description': 'Imágenes de fondo de la cabecera de inicio, términos y ayuda. Sólo una '
			               'configuración puede estar activa: al activar esta se desactivan las demás.',
			'fields': ('title', 'cover', 'term_cover', 'help_cover', 'is_active'),
		}),
		('Del diseño anterior', {
			'classes': ['collapse'],
			'description': 'El diseño actual no muestra estos campos; se conservan por si se retoman.',
			'fields': ('subtitle', 'subcover', 'service_cover'),
		}),
	)

	@display(description='Configuración', header=True)
	def settings(self, obj):
		picture = {'path': obj.cover.url, 'squared': True} if obj.cover else None
		return [obj.title, 'Fondo de inicio, términos y ayuda', None, picture]


@admin.register(Icons)
class IconsAdmin(SingleActiveAdmin):
	list_display = ('name', 'status')
	fieldsets = (
		(None, {
			'description': 'Fuente de íconos de las especificaciones. Expórtala desde IcoMoon con el prefijo '
			               'de clases «lb-» y sube los archivos de la carpeta fonts y el style.css. Sólo una '
			               'fuente puede estar activa.',
			'fields': ('name', 'is_active'),
		}),
		('Archivos', {'fields': ('css', 'woff', 'ttf', 'eot', 'svg')}),
	)


PLAIN_TEXT_HELP = ('Texto plano: los saltos de línea se respetan y una línea en blanco empieza otro '
                   'párrafo.')


class OrderedTextAdmin(ModelAdmin):
	"""Términos y Ayuda: se ordenan arrastrando las filas y su descripción es texto plano."""

	list_display = ('title', 'summary')
	search_fields = ('title', 'description')
	hide_ordering_field = True

	def get_form(self, request, obj=None, **kwargs):
		kwargs['help_texts'] = {'description': PLAIN_TEXT_HELP, **(kwargs.get('help_texts') or {})}
		return super().get_form(request, obj, **kwargs)

	def save_model(self, request, obj, form, change):
		if not change:  # lo nuevo va al final de la lista
			last = self.model.objects.aggregate(top=Max(self.ordering_field))['top'] or 0
			setattr(obj, self.ordering_field, last + 1)
		super().save_model(request, obj, form, change)

	@display(description='Descripción')
	def summary(self, obj):
		return Truncator(obj.description).chars(90)


@admin.register(Term)
class TermAdmin(OrderedTextAdmin):
	ordering_field = 'order'
	fields = ('title', 'description')


@admin.register(Help)
class HelpAdmin(OrderedTextAdmin):
	ordering_field = 'sequence'
	fields = ('title', 'description')

	def save_model(self, request, obj, form, change):
		obj.user = request.user
		super().save_model(request, obj, form, change)
