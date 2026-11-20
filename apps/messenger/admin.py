from django.contrib import admin
from django.db.models import Count, F, Max
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import display

from apps.project.admin_utils import short_date, short_datetime, user_header

from .models import Conversation, Message


class SuperuserReadOnlyMixin:
    """Mensajes privados entre usuarios: sólo los superusuarios los ven, y nadie los cambia desde aquí."""

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class MessageInline(SuperuserReadOnlyMixin, TabularInline):
    model = Message
    fields = ('author', 'message', 'sent', 'read_at')
    readonly_fields = fields
    ordering = ('create_date', 'pk')
    extra = 0
    tab = True
    show_title = False  # sin la fila "Message object (n)"
    verbose_name = 'mensaje'
    verbose_name_plural = 'Mensajes'

    @display(description='Autor')
    def author(self, obj):
        return obj.sender.get_full_name() or obj.sender.get_username()

    # Message no tiene verbose_name en estos campos: sin estas columnas se verían "Content" y "Create date".
    @display(description='Mensaje')
    def message(self, obj):
        return obj.content

    @display(description='Enviado')
    def sent(self, obj):
        return short_datetime(obj.create_date)


@admin.register(Conversation)
class ConversationAdmin(SuperuserReadOnlyMixin, ModelAdmin):
    list_display = ('starter', 'recipient', 'messages_total', 'last_activity', 'started')
    list_select_related = ('owner__profile', 'member__profile')
    list_filter = (('create_date', RangeDateFilter),)
    list_filter_submit = True
    search_fields = ('owner__email', 'owner__first_name', 'owner__last_name',
                     'member__email', 'member__first_name', 'member__last_name')
    list_before_template = 'admin/messenger/privacy_notice.html'
    change_form_before_template = 'admin/messenger/privacy_notice.html'
    fields = ('starter_detail', 'recipient_detail', 'create_date')
    readonly_fields = fields
    inlines = [MessageInline]

    def get_ordering(self, request):
        # Primero las que tienen actividad reciente; las vacías, al final.
        return [F('last_message_at').desc(nulls_last=True), '-create_date']

    def get_queryset(self, request):
        # Se anota antes de ordenar: el get_queryset de Django aplica get_ordering, que usa last_message_at.
        queryset = self.model._default_manager.annotate(
            messages_count=Count('messages', distinct=True), last_message_at=Max('messages__create_date'),
        )
        return queryset.order_by(*self.get_ordering(request))

    @display(description='Inició', header=True)
    def starter(self, obj):
        return user_header(obj.owner)

    @display(description='Con', header=True)
    def recipient(self, obj):
        return user_header(obj.member)

    @display(description='Inició')
    def starter_detail(self, obj):
        return f'{obj.owner.get_full_name() or obj.owner.get_username()} ({obj.owner.email})'

    @display(description='Con')
    def recipient_detail(self, obj):
        return f'{obj.member.get_full_name() or obj.member.get_username()} ({obj.member.email})'

    @display(description='Mensajes', ordering='messages_count')
    def messages_total(self, obj):
        return obj.messages_count

    @display(description='Último mensaje', ordering='last_message_at', empty_value='—')
    def last_activity(self, obj):
        return short_date(obj.last_message_at)

    @display(description='Creada', ordering='create_date')
    def started(self, obj):
        return short_date(obj.create_date)
