from django.http import HttpResponse, JsonResponse, Http404
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

class PropertyUpdateView(PropertyViewMixin, UpdateView):    
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.object = self.get_object() 
        image_form = ImageForm(initial = {
            'object_id': self.object.id,
            'content_type': ContentType.objects.get_for_model(self.object)
        })
        more_for_this_user = self.model.objects.filter(user=self.object.user).exclude(pk=self.object.pk)
        
        context.update({
            'image_form': image_form,
            'more_for_this_user': more_for_this_user,
        })

        return context


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
        pdf = get_pdf(self.object)
        # Get the value of the StringIO buffer and write it to the response.
        response.write(pdf)
        return response

class PropertyDeleteView(DeleteView):
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

        if not is_pay(self.object, request.user):
            return redirect(reverse_lazy('detail_property', args=[self.object.id,]))
        
        return super().get(request, *args, **kwargs)



class FinderMapView(FormView) :    
    template_name = 'realty/finder.html'
    form_class = FinderForm

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

class FinderListView(FinderMapView) :    
    template_name = 'realty/finder_without_map.html'
    form_class = FinderForm


##Ajax components
class PropertyDetailsRenderer(FormView):
    template_name = 'realty/publication_details.html'
    form_class = GroupDetailsForm
    http_method_names = ['get',]

    def get(self, request, *args, **kwargs):
        if not self.request.is_ajax(): 
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

class DetailsView(FormView):
    form_class = GroupDetailsForm
    http_method_names = ['get',]

    def get(self, request, *args, **kwargs):
        if not self.request.is_ajax(): raise Http404
        forms = []
        for group in self.get_groups():
            forms.append(self.get_form(group))
        r = render_to_string('components/realty/publication_details.html', context={'forms':forms})
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
        
