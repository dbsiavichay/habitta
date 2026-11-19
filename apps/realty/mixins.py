from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect

from apps.multimedia.forms import CoverImageForm

from .forms import GroupDetailsForm, LocationForm, PropertyForm
from .models import Category, Property, Specification


class PropertyViewMixin:
    """Lógica compartida de crear y editar un anuncio (asistente de publicación).

    Además del PropertyForm (propósito, título, descripción) el asistente envía en el mismo POST
    los formularios de especificaciones (uno por grupo de la categoría), la ubicación y la portada.
    """
    model = Property
    form_class = PropertyForm
    template_name = 'realty/property_form.html'

    # Paso del asistente donde vive cada formulario (1 datos, 2 ubicación, 3 portada)
    STEP_DATA, STEP_LOCATION, STEP_COVER = 1, 2, 3

    def get_category(self):
        """Al editar, la del anuncio; al crear, la de la URL (debe estar habilitada). Nunca la del POST."""
        if getattr(self, 'object', None) is not None and self.object.pk:
            return self.object.category
        category = get_object_or_404(Category, pk=self.kwargs.get('category'))
        if not category.enabled:
            raise Http404
        return category

    def get_form_kwargs(self):
        self.category = self.get_category()
        kwargs = super().get_form_kwargs()
        kwargs['category'] = self.category
        return kwargs

    def get_wizard_forms(self):
        """Formularios secundarios, construidos una sola vez por petición."""
        if not hasattr(self, '_wizard_forms'):
            self._wizard_forms = {
                'details_forms': self.get_details_forms(),
                'location_form': self.get_location_form(),
                'cover_form': self.get_cover_form(),
            }
        return self._wizard_forms

    def form_valid(self, form):
        forms = self.get_wizard_forms()
        details_forms, location_form, cover_form = forms['details_forms'], forms['location_form'], forms['cover_form']
        # Se validan todos (no se corta en el primero) para mostrar todos los errores de una vez
        valid = [f.is_valid() for f in details_forms] + [location_form.is_valid(), cover_form.is_valid()]
        if not all(valid):
            return self.form_invalid(form)

        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.category = self.category
            self.object.address = location_form.cleaned_data['address']
            self.object.geopoint = location_form.get_geopoint()
            self.object.radius = location_form.cleaned_data['radius']
            self.object.details = {
                'purpose': form.cleaned_data['purpose'].id,
                'specifications': self.get_form_specifications(details_forms),
            }
            if not self.object.user_id:
                self.object.user = self.request.user
            self.object.save()
            self.save_cover(cover_form, self.object)
        return redirect(self.get_success_url())

    def get_form_specifications(self, forms):
        specifications = {}
        for form in forms:
            specifications.update(form.get_not_empty_cleaned_data())
        return specifications

    def get_initial_step(self, form, forms):
        """Primer paso con errores tras un POST inválido (el asistente se abre ahí)."""
        if self.request.method != 'POST':
            return self.STEP_DATA
        if form.errors or any(f.errors for f in forms['details_forms']):
            return self.STEP_DATA
        if forms['location_form'].errors:
            return self.STEP_LOCATION
        if forms['cover_form'].errors:
            return self.STEP_COVER
        return self.STEP_DATA

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        forms = self.get_wizard_forms()
        context.update(forms)
        price = None
        if self.category.price_area:
            price = Specification.objects.filter(internal_name__iexact=self.category.price_area).only('pk').first()
        cover = self.object.get_cover_instance() if self.object is not None else None
        context.update({
            'category': self.category,
            'initial_step': self.get_initial_step(context['form'], forms),
            # Campo del precio (para mostrarlo con formato en el paso Revisar)
            'price_field': str(price.pk) if price else '',
            'current_cover': cover.img.url if cover and cover.img else '',
        })
        return context

    def get_details_forms(self):
        return [
            GroupDetailsForm(**self.get_kwargs(group=group))
            for group in self.category.groups.all().order_by('groupcategory__sequence').prefetch_related('specifications')
        ]

    def get_location_form(self):
        kwargs = self.get_kwargs(require_location=self.category.require_location)
        if self.object is not None and self.object.geopoint is not None:
            kwargs['initial'] = {
                'longitude': self.object.geopoint.x,
                'latitude': self.object.geopoint.y,
                'radius': self.object.radius,
                'address': self.object.address,
            }
        return LocationForm(**kwargs)

    def get_cover_form(self):
        return CoverImageForm(**self.get_kwargs())

    def get_kwargs(self, **kwargs):
        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs

    def save_cover(self, form, obj):
        from PIL import Image
        from apps.multimedia.utils import compress_image

        cover = form.save(commit=False)
        if cover:
            cover.object_id = obj.id
            cover.content_type = ContentType.objects.get_for_model(obj)
            cover.save()
            path = cover.img.path
            compress_image(path)
            # Miniatura que usan las tarjetas (srcset 320w)
            with Image.open(path) as im:
                im.thumbnail((320, 180))
                obj.update_image(im, 'thumbnail')
