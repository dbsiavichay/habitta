from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, OuterRef, Q, Subquery
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView

from apps.multimedia.forms import ImageForm


from .models import Category, Property
from .mixins import PropertyViewMixin
from .search import search_data
from .utils import property_photos
from apps.authentication.mixins import OwnerQuerysetMixin
from apps.project.templatetags.habitta import KIND_ICONS, KIND_LABELS

from apps.logs.models import Log

from .report import get_pdf

#For download object
import os
import zipfile
from io import BytesIO


class ChooseCategoryListView(ListView):
    """Paso 1 del asistente: elegir la categoría, agrupadas por tipo (inmuebles, servicios, empleos)."""
    model = Category
    template_name = 'realty/choose_category.html'

    def get_queryset(self):
        return Category.objects.filter(enabled=True).prefetch_related('purposes').order_by('kind', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        by_kind = {kind: [] for kind, _ in Category.KIND_CHOICES}
        for category in context['object_list']:
            by_kind.setdefault(category.kind, []).append(category)
        kind = self.request.GET.get('kind', '')
        context.update({
            'kinds': [
                {'id': kind_id, 'label': KIND_LABELS[kind_id], 'icon': KIND_ICONS[kind_id], 'categories': by_kind[kind_id]}
                for kind_id, _ in Category.KIND_CHOICES if by_kind[kind_id]
            ],
            'initial_kind': int(kind) if kind in ('1', '2', '3') else Category.REAL_STATE,
        })
        return context


class PropertyListView(ListView):
    """Mis publicaciones."""
    model = Property
    paginate_by = 12

    def get_queryset(self):
        return (
            Property.objects.filter(user=self.request.user)
            .select_related('category')
            .annotate(likes=Count('log', filter=Q(log__type=Log.LIKE)))
            .order_by('-pub_date', '-pk')
        )


class PropertyCreateView(PropertyViewMixin, CreateView):
    def get_success_url(self):
        messages.success(self.request, '¡Tu anuncio está publicado! Ahora suma más fotos.')
        return reverse('property_photos', args=[self.object.pk]) + '?nuevo=1'


class PropertyUpdateView(OwnerQuerysetMixin, PropertyViewMixin, UpdateView):
    def get_previous_specifications(self):
        return (self.get_object().details or {}).get('specifications', {})

    def get_details_forms(self):
        forms = super().get_details_forms()
        previous = self.get_previous_specifications()
        for form in forms:
            if self.request.method == 'GET':
                form.initial = previous
            # Un archivo ya subido no se vuelve a pedir: sólo se reemplaza si se elige otro
            for key, field in form.fields.items():
                if field.__class__.__name__ == 'FileField' and previous.get(key):
                    field.required = False
                    field.help_text = 'Ya subiste un archivo. Elige otro sólo si quieres reemplazarlo.'
        return forms

    def get_form_specifications(self, forms):
        specifications = super().get_form_specifications(forms)
        previous = self.get_previous_specifications()
        for form in forms:
            for key, field in form.fields.items():
                if field.__class__.__name__ == 'FileField' and key not in specifications and previous.get(key):
                    specifications[key] = previous[key]
        return specifications

    def get_cover_form(self):
        form = super().get_cover_form()
        if self.request.method == 'POST':
            cover = self.get_object().get_cover_instance()
            if cover:
                form.instance = cover
        return form

    def get_success_url(self):
        messages.success(self.request, 'Guardamos los cambios de tu anuncio.')
        return self.object.get_absolute_url()


class PropertyPhotosView(OwnerQuerysetMixin, DetailView):
    """Último paso del asistente (y acceso directo desde Mis publicaciones): fotos de la galería."""
    model = Property
    template_name = 'realty/property_photos.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'photos': property_photos(self.object),
            'content_type_id': ContentType.objects.get_for_model(Property).id,
            'is_new': 'nuevo' in self.request.GET,
        })
        return context

class PropertyDetailView(DetailView):
    model = Property
    queryset = Property.objects.select_related('category', 'user__profile')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        content_type = ContentType.objects.get_for_model(self.object)
        image_form = ImageForm(initial = {
            'object_id': self.object.id,
            'content_type': content_type,
        })
        more_for_this_user = (
            self.model.objects.filter(user=self.object.user)
            .exclude(pk=self.object.pk)
            .select_related('category', 'user__profile')[:8]
        )

        context.update({
            'image_form': image_form,
            'content_type_id': content_type.id,
            'more_for_this_user': more_for_this_user,
            'photos': self.get_photos(),
            'map_point': self.get_map_point(),
        })

        return context

    def get_photos(self):
        return property_photos(self.object)

    def get_map_point(self):
        point = self.object.geopoint
        if not point:
            return None
        radius = None if self.object.category.require_location else self.object.radius
        if not self.object.category.require_location and not radius:
            return None
        return {'lat': point.y, 'lng': point.x, 'radius': radius or 0}


class PropertyFavoriteListView(ListView):
    """Favoritos: anuncios con "me gusta" del usuario, el último guardado primero."""
    model = Property
    template_name_suffix = '_favorite_list'
    paginate_by = 12

    def get_queryset(self):
        likes = Log.objects.filter(type=Log.LIKE, user=self.request.user, property=OuterRef('pk'))
        return (
            Property.objects.filter(log__type=Log.LIKE, log__user=self.request.user)
            .select_related('category', 'user__profile')
            .annotate(like_id=Subquery(likes.values('pk')[:1]), liked_at=Subquery(likes.values('date')[:1]))
            .order_by('-liked_at')
        )

class PropertyPrintView(DetailView):
    model = Property

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        response = HttpResponse(content_type='application/pdf')
        # Para visualizar en el navegador
        #response['Content-Disposition'] = 'inline; filename=report.pdf'
        # Para descargar
        response['Content-Disposition'] = 'attachment; filename="property.pdf"' 
        pdf = get_pdf(self.object, base_url=settings.SITE_URL or request.build_absolute_uri('/').rstrip('/'))
        # Get the value of the StringIO buffer and write it to the response.
        response.write(pdf)
        return response

class PropertyDeleteView(OwnerQuerysetMixin, DeleteView):
    model = Property
    success_url = reverse_lazy('properties')
    http_method_names = ['post',]

    def form_valid(self, form):
        messages.success(self.request, 'Eliminamos el anuncio «%s».' % (self.object.title or self.object.category.singular_name))
        return super().form_valid(form)

class PropertyDownloadView(DetailView):
    model = Property

    def render_to_response(self, context, **httpresponse_kwargs):		
        dirname = u'download_files_{0}'.format(self.object.id)
        filename = u'{0}.zip'.format(dirname)

        buffer = BytesIO()
        z = zipfile.ZipFile(buffer, 'w')

        for path in self.object.get_path_files():						
            z.write(path, os.path.join(dirname, os.path.basename(path)))
        z.close()
        buffer.seek(0)
        response = HttpResponse(buffer.read())
        response['Content-Disposition'] = u'attachment; filename={0}'.format(filename)
        response['Content-Type'] = 'application/x-zip'
        return response

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        from apps.payments.templatetags.payments import is_pay

        is_owner = self.object.user == request.user or request.user.is_superuser
        if not is_owner and not is_pay(self.object, request.user):
            return redirect(reverse_lazy('detail_property', args=[self.object.id,]))
        
        return super().get(request, *args, **kwargs)



class FinderMapView(TemplateView):
    """Explorador de anuncios (lista + mapa). Los filtros llegan por GET (URL compartible).

    También acepta el POST de los buscadores antiguos (search_purpose, search_category, search_address).
    """
    template_name = 'realty/finder.html'
    initial_view = 'map'

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def get_initial_filters(self):
        data = self.request.POST if self.request.method == 'POST' else self.request.GET

        def number(name):
            value = data.get(name, '')
            try:
                float(value)
                return value
            except ValueError:
                return ''

        return {
            'kind': data.get('kind', '') if data.get('kind') in ('1', '2', '3') else '',
            'purpose': number('search_purpose'),
            'category': number('search_category'),
            'address': data.get('search_address', '')[:120],
            'lat': number('lat'),
            'lng': number('lng'),
            'radius': number('radius') or '15',
            'minPrice': number('min_price'),
            'maxPrice': number('max_price'),
            'view': data.get('view') if data.get('view') in ('map', 'list') else self.initial_view,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'search_data': search_data(),
            'initial_filters': self.get_initial_filters(),
        })
        return context

class FinderListView(FinderMapView):
    initial_view = 'list'

