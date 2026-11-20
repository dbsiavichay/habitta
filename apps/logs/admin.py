from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateFilter, RelatedDropdownFilter
from unfold.decorators import display

from apps.project.admin_utils import short_date, site_link, user_header

from .models import Log

TYPE_LABEL = {Log.VIEW: 'info', Log.LIKE: 'danger'}


@admin.register(Log)
class LogAdmin(ModelAdmin):
    """Vistas y "me gusta" de las publicaciones (un registro por usuario, publicación y tipo). Sólo consulta."""

    list_display = ('kind', 'listing', 'person', 'when')
    list_select_related = ('property', 'user__profile')
    list_filter = (('type', ChoicesDropdownFilter), ('property', RelatedDropdownFilter), ('date', RangeDateFilter))
    list_filter_submit = True
    search_fields = ('property__title', 'user__email', 'user__first_name', 'user__last_name')
    ordering = ('-date',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @display(description='Tipo', label=TYPE_LABEL, ordering='type')
    def kind(self, obj):
        return obj.type, obj.get_type_display()

    @display(description='Publicación', ordering='property__title')
    def listing(self, obj):
        return site_link(obj.property, obj.property.title)

    @display(description='Usuario', header=True)
    def person(self, obj):
        return user_header(obj.user)

    @display(description='Fecha', ordering='date')
    def when(self, obj):
        return short_date(obj.date)
