from django.contrib import admin

from .models import Comment


# Los comentarios no se muestran en el sitio; se conservan los datos y se pueden revisar desde aquí.
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
	list_display = ('__str__', 'user', 'contenttype', 'object_id', 'date')
	list_select_related = ('user', 'contenttype')
