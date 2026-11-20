from django.contrib import admin
from django.utils.text import Truncator
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import display

from apps.project.admin_utils import short_date, user_header

from .models import Comment


# Los comentarios no se muestran en el sitio; se conservan los datos y se pueden revisar desde aquí.
@admin.register(Comment)
class CommentAdmin(ModelAdmin):
	list_display = ('summary', 'author', 'about', 'when')
	list_select_related = ('user__profile', 'contenttype')
	list_filter = (('date', RangeDateFilter),)
	list_filter_submit = True
	search_fields = ('content', 'user__email', 'user__first_name', 'user__last_name')
	fields = ('author_detail', 'about', 'content', 'date')
	readonly_fields = fields

	def has_add_permission(self, request):
		return False

	def has_change_permission(self, request, obj=None):
		return False

	@display(description='Comentario')
	def summary(self, obj):
		return Truncator(obj.content or '').chars(80) or '—'

	@display(description='Autor', header=True)
	def author(self, obj):
		return user_header(obj.user)

	@display(description='Autor')
	def author_detail(self, obj):
		return obj.user.get_full_name() or obj.user.get_username()

	@display(description='Sobre')
	def about(self, obj):
		model = obj.contenttype.model_class()
		target = model._default_manager.filter(pk=obj.object_id).first() if model else None
		return f'{obj.contenttype.name}: {target}' if target else 'Ya no existe'

	@display(description='Fecha', ordering='date')
	def when(self, obj):
		return short_date(obj.date)
