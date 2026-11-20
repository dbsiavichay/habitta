from django.contrib import admin
from django.urls import NoReverseMatch
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RelatedDropdownFilter
from unfold.decorators import display

from apps.project.admin_utils import admin_link, image_preview, thumbnail

from .models import Image

ROLES = {'thumbnail': 'Miniatura', 'map': 'Mapa estático'}


@admin.register(Image)
class ImageAdmin(ModelAdmin):
	"""Imágenes de anuncios y redes sociales. Se suben desde el sitio; aquí sólo se consultan o se borran
	(al borrar una fila también se borra su archivo)."""

	list_display = ('picture', 'role', 'owner_type', 'owner')
	list_select_related = ('content_type',)
	list_filter = (('content_type', RelatedDropdownFilter), 'is_cover', 'code')
	list_filter_submit = True
	ordering = ('-pk',)
	fields = ('preview', 'role', 'owner_type', 'owner')
	readonly_fields = fields

	def has_add_permission(self, request):
		return False

	def has_change_permission(self, request, obj=None):
		return False

	@display(description='Imagen')
	def picture(self, obj):
		return thumbnail(obj.img.url, 48) if obj.img else '—'

	@display(description='Imagen')
	def preview(self, obj):
		return image_preview(obj.img, height=320)

	@display(description='Uso')
	def role(self, obj):
		return ROLES.get(obj.code) or ('Portada' if obj.is_cover else 'Galería')

	@display(description='Tipo de dueño', ordering='content_type')
	def owner_type(self, obj):
		return obj.content_type.name

	def get_queryset(self, request):
		# Un solo query por tipo de dueño (GenericForeignKey) en vez de uno por fila.
		return super().get_queryset(request).prefetch_related('content_object')

	@display(description='Pertenece a')
	def owner(self, obj):
		target = obj.content_object
		if target is None:
			return 'Ya no existe'
		try:
			return admin_link(target)
		except NoReverseMatch:  # el dueño no tiene pantalla en el admin
			return str(target)
