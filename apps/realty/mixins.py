from django.shortcuts import redirect, get_object_or_404
from django.http import Http404
from django.urls import reverse_lazy
from django.contrib.contenttypes.models import ContentType
from .models import Property, Category
from .forms import PropertyForm, GroupDetailsForm, LocationForm
from apps.multimedia.forms import CoverImageForm


class PropertyViewMixin:
    model = Property
    form_class = PropertyForm
    success_url = reverse_lazy('properties')

    def form_valid(self, form):     
        self.category = self.get_category(form.data.get('category'))        
        details_forms = self.get_details_forms()        
        cover_form = self.get_cover_form()

        location_valid = True
        #if self.category.require_location:
        location_form = self.get_location_form()
        location_valid = location_form.is_valid()

        for dform in details_forms:
            if not dform.is_valid(): return self.form_invalid(form)

        if not cover_form.is_valid() or not location_valid:
            return self.form_invalid(form)

        details = {
            'purpose': form.cleaned_data['purpose'].id,
            'specifications': self.get_form_specifications(details_forms),
        }   

        self.object = form.save(commit=False)
        #if self.category.require_location:
        print(location_form.cleaned_data['radius'])
        self.object.address = location_form.cleaned_data['address']
        self.object.geopoint = location_form.get_geopoint()
        self.object.radius = location_form.cleaned_data['radius']

        self.object.details = details
        if not hasattr(self.object, 'user'):
            self.object.user = self.request.user
        #self.object.category = self.category
        self.object.save()

        self.save_cover(cover_form, self.object)
        return redirect(self.object.get_absolute_url())

    def get_form_specifications(self, forms):
        specifications = {}
        for form in forms:
            specifications.update(form.get_not_empty_cleaned_data())

        return specifications

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        #if self.category.require_location:
        #    context.update({'location_form': self.get_location_form(),})
        context.update({'location_form': self.get_location_form(),})

        context.update({            
            'cover_form': self.get_cover_form(),
        })

        if not self.get_kind():
            context.update({
                'details_forms': self.get_details_forms(),              
            })      
        return context
        
    def get_category(self, pk=None):
        pk = pk or self.kwargs.get('category')
        if pk is not None:      
            category = get_object_or_404(Category, pk=pk)
        else:
            category = self.get_object().category

        return category

    def get_kind(self):
        pk = self.request.GET.get('kind')
        if not pk:
            return
        try:
            pk = int(pk)
            if pk == Category.REAL_STATE or pk == Category.SERVICE:
                return pk           
        except:
            pass

        raise Http404

    def get_form_kwargs(self):
        self.kind = self.get_kind()
        self.category = self.get_category() 
        kwargs = super().get_form_kwargs()          
        kwargs.update({'category': self.category, 'kind': self.kind})
        return kwargs

    def get_details_forms(self):    
        forms = []
        for group in self.category.groups.all().order_by('groupcategory__sequence'):            
            form = GroupDetailsForm(**self.get_kwargs(group=group))
            forms.append(form)
        return forms

    def get_location_form(self):
        kwargs = self.get_kwargs()
        kwargs.update({'require_location': self.category.require_location})
        if self.object is not None and self.object.geopoint is not None:
            initials = {'longitude':self.object.geopoint.x, 'latitude': self.object.geopoint.y, 'radius': self.object.radius}
            kwargs.update({'initial': initials})
        form = LocationForm(**kwargs)
        return form

    def get_cover_form(self):               
        form = CoverImageForm(**self.get_kwargs())
        return form

    def get_kwargs(self, **kwargs):
        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs

    def save_cover(self, form, obj):
        import tinify
        import os
        from django.conf import settings
        from PIL import Image

        cover = form.save(commit=False)
        if cover:
            cover.object_id = obj.id
            cover.content_type = ContentType.objects.get_for_model(obj)
            cover.save()
            #Tinify
            tinify.key = settings.TINIFY_API_KEY
            path = cover.img.path
            source = tinify.from_file(path)
            source.to_file(path)
            #Thumbnail
            size = 320, 180
            im = Image.open(path)
            im.thumbnail(size)
            obj.update_image(im, 'thumbnail')