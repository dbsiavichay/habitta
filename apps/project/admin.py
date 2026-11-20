from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Settings, Icons, Term, Help

# Título de la barra superior en el inicio (por defecto "Sitio administrativo"). La marca, el menú
# y el dashboard se configuran en config/unfold.py.
admin.site.index_title = 'Inicio'


class SingleActiveAdmin(ModelAdmin):
	"""Sólo una fila puede estar activa: al activar una se desactivan las demás."""

	def save_model(self, request, obj, form, change):
		if obj.is_active:
			self.model.objects.all().update(is_active=False)
		super().save_model(request, obj, form, change)


@admin.register(Settings)
class SettingsAdmin(SingleActiveAdmin):
	list_display = ('title', 'subtitle', 'cover', 'is_active')


@admin.register(Icons)
class IconsAdmin(SingleActiveAdmin):
	list_display = ('name', 'is_active')


@admin.register(Term)
class TermAdmin(ModelAdmin):
	pass


@admin.register(Help)
class HelpAdmin(ModelAdmin):
	exclude = ('user',)

	def save_model(self, request, obj, form, change):
		obj.user = request.user
		super().save_model(request, obj, form, change)
