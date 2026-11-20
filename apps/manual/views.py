from django.http import Http404
from django.urls import reverse
from django.views.generic import TemplateView

from apps.payments.views import get_server_price
from apps.realty.models import Category

from .content import MANUALS, render_markdown


def purchasable_categories():
    """Categorías en las que hoy se pueden comprar archivos: marcadas como vendibles y con algún
    anuncio que tenga precio (sin precio, el pago se rechaza)."""
    return [
        category.name
        for category in Category.objects.filter(is_salable=True).prefetch_related('property_set').order_by('name')
        if any(get_server_price(listing) for listing in category.property_set.all())
    ]


class ManualHubView(TemplateView):
    """Portada de los manuales: los dos manuales y cómo probar el demo."""
    template_name = 'manual/hub.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['manuals'] = list(MANUALS.values())
        context['demo_html'], _ = render_markdown(
            'manual/demo.md', self.request, {'purchasable_categories': purchasable_categories()},
        )
        return context


class ManualMixin:
    def get_manual(self):
        manual = MANUALS.get(self.kwargs['manual'])
        if manual is None:
            raise Http404('No existe ese manual.')
        return manual

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manual = self.get_manual()
        context['manual'] = manual
        context['chapters'] = [
            {'number': number, 'chapter': chapter, 'url': manual.chapter_url(chapter)}
            for number, chapter in enumerate(manual.chapters, start=1)
        ]
        context['other_manuals'] = [other for other in MANUALS.values() if other != manual]
        return context


class ManualIndexView(ManualMixin, TemplateView):
    template_name = 'manual/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manual = context['manual']
        context['crumbs'] = [('Manuales', reverse('manual')), (manual.title, '')]
        return context


class ManualChapterView(ManualMixin, TemplateView):
    template_name = 'manual/chapter.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manual = context['manual']
        chapter = manual.chapter(self.kwargs['chapter'])
        if chapter is None:
            raise Http404('No existe ese capítulo.')
        previous, following = manual.neighbors(chapter)
        context.update({
            'chapter': chapter,
            'number': manual.chapters.index(chapter) + 1,
            'previous': previous and {'chapter': previous, 'url': manual.chapter_url(previous)},
            'next': following and {'chapter': following, 'url': manual.chapter_url(following)},
            'crumbs': [('Manuales', reverse('manual')), (manual.title, manual.get_absolute_url()), (chapter.title, '')],
        })
        context['body'], context['toc'] = render_markdown(
            manual.template_name(chapter), self.request, {'manual': manual, 'chapter': chapter},
        )
        return context
