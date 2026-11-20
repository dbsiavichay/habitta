from django.contrib import admin, messages
from django.db.models import Count, Max
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.text import Truncator
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateFilter
from unfold.decorators import action, display
from unfold.enums import ActionVariant

from apps.project.admin_utils import (
    ReadOnlyChangeFormMixin, back_to_page, label_html, short_date, site_link, user_header,
)
from apps.project.templatetags.habitta import money

from .models import Auction, Offer

STAGE_LABEL = {Auction.OPEN: 'success', Auction.CLOSED: 'info', Auction.CANCELED: 'danger'}


class OfferInline(TabularInline):
    model = Offer
    fields = ('bidder', 'amount_display', 'date')
    readonly_fields = fields
    ordering = ('-amount', 'date')
    extra = 0
    can_delete = False
    tab = True
    verbose_name = 'oferta'
    verbose_name_plural = 'Ofertas'

    def has_add_permission(self, request, obj=None):
        return False

    @display(description='Usuario')
    def bidder(self, obj):
        return obj.user.get_full_name() or obj.user.get_username()

    @display(description='Monto')
    def amount_display(self, obj):
        return money(obj.amount)


@admin.register(Auction)
class AuctionAdmin(ReadOnlyChangeFormMixin, ModelAdmin):
    """Subastas que crean los usuarios desde su panel. El equipo sólo puede consultarlas o cancelarlas."""

    list_display = ('listing', 'owner', 'stage_badge', 'base', 'best_offer', 'offers', 'starts', 'ends')
    list_select_related = ('property__user__profile',)
    list_filter = (('stage', ChoicesDropdownFilter), ('ending_date', RangeDateFilter))
    list_filter_submit = True
    search_fields = ('property__title', 'property__user__email', 'property__user__first_name', 'property__user__last_name')
    ordering = ('-start_date',)
    fields = ('listing_link', 'stage_detail', 'base', 'start_date', 'ending_date')
    readonly_fields = fields
    inlines = [OfferInline]
    actions_row = ('cancel_auction',)
    actions_detail = ('cancel_auction',)

    def has_add_permission(self, request):
        return False

    def get_actions_detail(self, request, object_id):
        # "Cancelar subasta" sólo tiene sentido mientras está abierta.
        if not Auction.objects.filter(pk=object_id, stage=Auction.OPEN).exists():
            return []
        return super().get_actions_detail(request, object_id)

    def get_queryset(self, request):
        # Mismo cierre perezoso que el sitio: las vencidas pasan a "Finalizado" antes de listarlas.
        Auction.objects.close_expired()
        return super().get_queryset(request).annotate(
            offers_count=Count('offer', distinct=True), best_amount=Max('offer__amount'),
        )

    # Algunos anuncios viejos no tienen título: str(property) cae a la descripción.
    @display(description='Publicación', ordering='property__title')
    def listing(self, obj):
        return Truncator(str(obj.property)).chars(40)

    @display(description='Publicación')
    def listing_link(self, obj):
        return site_link(obj.property, Truncator(str(obj.property)).chars(60))

    @display(description='Propietario', header=True)
    def owner(self, obj):
        return user_header(obj.property.user)

    @display(description='Etapa', label=STAGE_LABEL, ordering='stage')
    def stage_badge(self, obj):
        return obj.stage, obj.get_stage_display()

    @display(description='Etapa')
    def stage_detail(self, obj):
        return label_html(obj.get_stage_display(), STAGE_LABEL.get(obj.stage))

    @display(description='Monto base', ordering='base_amount')
    def base(self, obj):
        return money(obj.base_amount)

    @display(description='Mejor oferta', ordering='best_amount', empty_value='Sin ofertas')
    def best_offer(self, obj):
        return money(obj.best_amount) if obj.best_amount is not None else None

    @display(description='Ofertas', ordering='offers_count')
    def offers(self, obj):
        return obj.offers_count

    @display(description='Inicio', ordering='start_date')
    def starts(self, obj):
        return short_date(obj.start_date)

    @display(description='Cierre', ordering='ending_date')
    def ends(self, obj):
        return short_date(obj.ending_date)

    @action(
        description='Cancelar subasta', icon='block', variant=ActionVariant.DANGER, permissions=['change'],
        url_path='cancel',
        dialog={
            'title': '¿Cancelar esta subasta?',
            'description': 'Se cierra para siempre y ya no recibe ofertas. El propietario no recibe aviso.',
            'form_submit_text': 'Cancelar subasta',
        },
    )
    def cancel_auction(self, request, form, object_id):
        auction = get_object_or_404(Auction, pk=object_id)
        if auction.stage == Auction.OPEN:
            auction.stage = Auction.CANCELED
            auction.save(update_fields=['stage'])
            messages.success(request, 'Subasta cancelada.')
        else:
            messages.warning(request, 'La subasta ya no estaba abierta; no se cambió.')
        return back_to_page(request, reverse('admin:auctions_auction_changelist'))
