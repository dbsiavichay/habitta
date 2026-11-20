from django import forms
from django.contrib import admin, messages
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateFilter, RelatedDropdownFilter
from unfold.decorators import action, display
from unfold.enums import ActionVariant
from unfold.forms import BaseDialogForm
from unfold.widgets import UnfoldAdminTextareaWidget

from apps.project.admin_utils import (
    ReadOnlyChangeFormMixin, back_to_page, image_preview, is_image, label_html, message_count, short_datetime,
    site_link, user_header,
)
from apps.project.templatetags.habitta import money

from .models import Bank, BankPayment, Payment, PaypalPayment
from .notifications import notify_payment_status

# Texto e insignia de cada estado, pensados para quien revisa (en el sitio "Registro" se ve como "En revisión").
STATUS_TEXT = {Payment.REGISTRY: 'Por confirmar', Payment.CONFIRMED: 'Confirmado', Payment.REJECTED: 'Rechazado'}
STATUS_LABEL = {Payment.REGISTRY: 'warning', Payment.CONFIRMED: 'success', Payment.REJECTED: 'danger'}


class RejectPaymentForm(BaseDialogForm):
    reason = forms.CharField(
        label='Motivo (opcional)', required=False, max_length=500,
        help_text='Se incluye en el correo al usuario. Por ejemplo: el comprobante no se lee o el monto no coincide.',
        widget=UnfoldAdminTextareaWidget(attrs={'rows': 3}),
    )


class PaymentDisplayMixin:
    """Columnas comunes de las transferencias y los pagos PayPal."""

    list_select_related = ('user__profile', 'content_type')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email')
    list_filter_submit = True

    @display(description='Usuario', header=True, ordering='user__first_name')
    def payer(self, obj):
        return user_header(obj.user)

    @display(description='Usuario')
    def payer_detail(self, obj):
        user = obj.user
        return format_html('{} · <a href="mailto:{}" class="text-primary-600 dark:text-primary-500">{}</a>',
                           user.get_full_name() or user.get_username(), user.email, user.email)

    @display(description='Monto', ordering='amount')
    def amount_display(self, obj):
        return money(obj.amount)

    @display(description='Estado', label=STATUS_LABEL, ordering='status')
    def status_badge(self, obj):
        return obj.status, STATUS_TEXT.get(obj.status, obj.get_status())

    @display(description='Estado')
    def status_detail(self, obj):
        return label_html(STATUS_TEXT.get(obj.status, obj.get_status()), STATUS_LABEL.get(obj.status))

    @display(description='Pagado por')
    def paid_for(self, obj):
        target = obj.get_object_or_none()
        if target is None:
            return 'Ya no existe'
        return site_link(target, str(target))

    @display(description='Fecha', ordering='date')
    def date_display(self, obj):
        return short_datetime(obj.date)


@admin.register(BankPayment)
class BankPaymentAdmin(ReadOnlyChangeFormMixin, PaymentDisplayMixin, ModelAdmin):
    list_display = ('payer', 'status_badge', 'amount_display', 'bank_name', 'paid_for', 'date_display')
    list_select_related = ('user__profile', 'content_type', 'bank')
    list_filter = (
        ('status', ChoicesDropdownFilter),
        ('bank', RelatedDropdownFilter),
        ('date', RangeDateFilter),
    )
    # Las pendientes primero; dentro de cada estado, las más recientes.
    ordering = ('status', '-date')
    fields = ('payer_detail', 'status_detail', 'amount_display', 'bank', 'paid_for', 'voucher_preview', 'date_display')
    readonly_fields = fields
    actions = ('confirm_selected', 'reject_selected')
    actions_row = ('confirm_payment', 'reject_payment')
    actions_detail = ('confirm_payment', 'reject_payment')

    @display(description='Banco', ordering='bank__name')
    def bank_name(self, obj):
        return obj.bank.name

    def get_actions_detail(self, request, object_id):
        # En la ficha, Confirmar/Rechazar sólo aparecen mientras la transferencia espera revisión.
        # (En las filas Unfold no las filtra por registro: ahí la acción avisa y no cambia nada.)
        if not BankPayment.objects.filter(pk=object_id, status=Payment.REGISTRY).exists():
            return []
        return super().get_actions_detail(request, object_id)

    def has_add_permission(self, request):
        # Las transferencias las registra cada usuario desde el sitio, con su comprobante.
        return False

    @display(description='Comprobante')
    def voucher_preview(self, obj):
        if not obj.voucher:
            return '—'
        if is_image(obj.voucher):
            return image_preview(obj.voucher, height=360)
        return format_html(
            '<a href="{}" target="_blank" rel="noopener" class="inline-flex items-center gap-1 font-medium '
            'text-primary-600 dark:text-primary-500"><span class="material-symbols-outlined">description</span>'
            'Abrir el comprobante</a>', obj.voucher.url,
        )

    # ---------- Cambios de estado (avisan al usuario por correo) ----------

    def _resolve(self, request, payments, status, reason=''):
        changed = skipped = unsent = 0
        for payment in payments:
            if payment.status != Payment.REGISTRY:
                skipped += 1
                continue
            payment.status = status
            payment.save(update_fields=['status'])
            changed += 1
            if not notify_payment_status(payment, request, reason):
                unsent += 1

        verb = 'confirmada' if status == Payment.CONFIRMED else 'rechazada'
        message_count(request, changed, f'Transferencia {verb}; avisamos al usuario por correo.',
                      f'{{count}} transferencias {verb}s; avisamos a cada usuario por correo.')
        message_count(request, unsent, 'No se pudo enviar el correo de aviso (revisa que el usuario tenga correo).',
                      'No se pudieron enviar {count} correos de aviso.', messages.WARNING)
        message_count(request, skipped, 'Esa transferencia ya estaba resuelta; no se cambió.',
                      '{count} transferencias ya estaban resueltas; no se cambiaron.', messages.WARNING)

    def _resolve_one(self, request, object_id, status, reason=''):
        payment = get_object_or_404(BankPayment.objects.select_related('user'), pk=object_id)
        self._resolve(request, [payment], status, reason)
        return back_to_page(request, reverse('admin:payments_bankpayment_change', args=[payment.pk]))

    @action(
        description='Confirmar', icon='check_circle', variant=ActionVariant.SUCCESS, permissions=['change'],
        url_path='confirm',
        dialog={
            'title': '¿Confirmar esta transferencia?',
            'description': 'Revisa que el comprobante y el monto coincidan. Al confirmar se habilitan las '
                           'descargas y se avisa al usuario por correo.',
            'form_submit_text': 'Confirmar pago',
        },
    )
    def confirm_payment(self, request, form, object_id):
        return self._resolve_one(request, object_id, Payment.CONFIRMED)

    @action(
        description='Rechazar', icon='cancel', variant=ActionVariant.DANGER, permissions=['change'],
        url_path='reject',
        dialog={
            'title': '¿Rechazar esta transferencia?',
            'description': 'El usuario recibirá un correo con el motivo y podrá registrar el pago de nuevo.',
            'form_class': RejectPaymentForm,
            'form_submit_text': 'Rechazar pago',
        },
    )
    def reject_payment(self, request, form, object_id):
        return self._resolve_one(request, object_id, Payment.REJECTED, form.cleaned_data['reason'])

    @action(description='Confirmar las transferencias seleccionadas', permissions=['change'])
    def confirm_selected(self, request, queryset):
        self._resolve(request, queryset.select_related('user'), Payment.CONFIRMED)

    @action(description='Rechazar las transferencias seleccionadas', permissions=['change'])
    def reject_selected(self, request, queryset):
        self._resolve(request, queryset.select_related('user'), Payment.REJECTED)


@admin.register(PaypalPayment)
class PaypalPaymentAdmin(PaymentDisplayMixin, ModelAdmin):
    """Sólo consulta: PayPal confirma o rechaza el pago al volver al sitio."""

    list_display = ('payer', 'status_badge', 'amount_display', 'payer_email', 'paid_for', 'date_display')
    list_filter = (('status', ChoicesDropdownFilter), ('date', RangeDateFilter))
    search_fields = PaymentDisplayMixin.search_fields + ('payer_email', 'payment_id')
    ordering = ('-date',)
    fields = ('payer_detail', 'status_detail', 'amount_display', 'paid_for', 'payer_email', 'payer_id', 'payment_id', 'date_display')
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Bank)
class BankAdmin(ModelAdmin):
    list_display = ('name', 'account_number', 'account_type', 'recipient_name', 'recipient_charter')
    search_fields = ('name', 'account_number', 'recipient_name')
    fieldsets = (
        ('Cuenta', {'fields': ('name', 'account_type', 'account_number')}),
        ('Beneficiario', {'fields': ('recipient_name', 'recipient_charter')}),
    )
