from django.conf import settings
from django.http import HttpResponse, JsonResponse, Http404
from hydra.utils import is_ajax
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse_lazy
from django.views.generic import (
    View, ListView, CreateView, UpdateView, DeleteView, DetailView, FormView, TemplateView
)

from django.template.loader import render_to_string

from apps.multimedia.forms import ImageForm


from .models import Category, Property, Purpose
from .forms import FinderForm, GroupDetailsForm
from .mixins import PropertyViewMixin
from .search import search_data
from apps.authentication.mixins import OwnerQuerysetMixin

from apps.logs.models import Log

from .report import get_pdf

#For download object
import os
import zipfile
from io import BytesIO

class ChooseCategoryListView(ListView):
    model = Category
    queryset = Category.objects.filter(enabled=True, kind=Category.REAL_STATE)
    template_name = 'realty/choose_category.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        services = self.model.objects.filter(enabled=True, kind=Category.SERVICE)
        jobs = self.model.objects.filter(enabled=True, kind=Category.JOB)
        context.update(
            {
                'services':services,
                'jobs': jobs
            }
        )
        return context

class PropertyListView(ListView):
    model = Property

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(user=self.request.user)


class PropertyCreateView(PropertyViewMixin, CreateView):
    def get(self, request, *args, **kwargs):
        category = self.get_category()
        if not category.enabled:
            raise Http404
        return super().get(request, *args, **kwargs)

class PropertyUpdateView(OwnerQuerysetMixin, PropertyViewMixin, UpdateView):
    def get_details_forms(self):
        forms = super().get_details_forms()
        if self.request.method == 'GET':
            try:
                initials = self.object.details['specifications']
                for form in forms:              
                    form.initial = initials
            except KeyError:
                pass

        return forms

    def get_cover_form(self):
        form = super().get_cover_form()
        if self.request.method == 'POST':       
            cover = self.get_object().get_cover_instance()          
            if cover:
                form.instance = cover
        return form

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
        """Portada + galería con sus dimensiones (las necesita el visor PhotoSwipe)."""
        photos = []
        cover = self.object.get_cover_instance()
        images = ([cover] if cover and cover.img else []) + self.object.get_gallery()
        seen = set()
        for image in images:
            # Las imágenes generadas para el PDF (QR, mapa estático, miniatura) no son fotos del anuncio
            if image.pk in seen or image.code in ('qrcode', 'map', 'thumbnail'):
                continue
            seen.add(image.pk)
            try:
                width, height = image.img.width, image.img.height
            except (OSError, ValueError):
                # La imagen no existe en el almacenamiento: no se muestra
                continue
            photos.append({
                'id': image.pk,
                'url': image.img.url,
                'width': width,
                'height': height,
                'is_cover': image.is_cover,
                'delete_url': reverse_lazy('delete_image', args=[image.pk]),
            })
        return photos

    def get_map_point(self):
        point = self.object.geopoint
        if not point:
            return None
        radius = None if self.object.category.require_location else self.object.radius
        if not self.object.category.require_location and not radius:
            return None
        return {'lat': point.y, 'lng': point.x, 'radius': radius or 0}


class PropertyFavoriteListView(ListView):
    model = Property
    template_name_suffix = '_favorite_list'

    def get_queryset(self):
        properties = Log.objects.values_list('property_id', flat=True).filter(type=Log.LIKE, user=self.request.user)
        queryset = super().get_queryset()
        return queryset.filter(id__in=properties)

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


##Ajax components
class PropertyDetailsRenderer(FormView):
    template_name = 'realty/publication_details.html'
    form_class = GroupDetailsForm
    http_method_names = ['get',]

    def get(self, request, *args, **kwargs):
        if not is_ajax(self.request):
            raise Http404
        forms = []
        for group in self.get_groups():
            forms.append(self.get_form(group))
        r = render_to_string(self.template_name, context={'forms':forms})
        return JsonResponse({'form': r}, status=200)

    def get_groups(self):
        pk = self.kwargs.get('category')
        category = get_object_or_404(Category, pk=pk)
        groups = category.groups.all().order_by('groupcategory__sequence')
        return groups

    def get_form(self, group, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        kwargs = self.get_form_kwargs()
        kwargs['group'] = group
        return form_class(**kwargs)



def filter_category_by_purpose(request, pk, klass): 
    purpose = get_object_or_404(Purpose, pk=pk)
    form = FinderForm(initial={'search_purpose': purpose})
    r = render_to_string('hydra/search_select.html', context={'form':form, 'klass':klass})
    
    return JsonResponse({'select': r}, status=200)

