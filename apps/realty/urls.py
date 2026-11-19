from django.urls import path
from django.contrib.auth.decorators import login_required
from .views import (
    ChooseCategoryListView, 
    PropertyListView, PropertyCreateView, PropertyUpdateView, PropertyDetailView, PropertyPrintView, PropertyDeleteView,
    PropertyFavoriteListView, PropertyDownloadView, PropertyPhotosView,
    FinderMapView, FinderListView, filter_category_by_purpose,
)

urlpatterns = [
    path('property/add/', login_required(ChooseCategoryListView.as_view()), name='choose_category'),
    path('publicationes/', login_required(PropertyListView.as_view()), name='properties'),

    path('property/add/category/<int:category>/', login_required(PropertyCreateView.as_view()), name='add_property'),
    #path('publicacion/crear/', login_required(PropertyCreateView.as_view()), name='add_property'),
    
    path('property/<int:pk>/update/', PropertyUpdateView.as_view(), name='update_property'),
    path('property/<int:pk>/fotos/', PropertyPhotosView.as_view(), name='property_photos'),
    path('property/<int:pk>/detail/', PropertyDetailView.as_view(), name='detail_property'),        
    path('property/<int:pk>/print/', PropertyPrintView.as_view(), name='print_property'),       
    path('property/<int:pk>/delete/', PropertyDeleteView.as_view(), name='delete_property'),        
    path('favorite/properties/', login_required(PropertyFavoriteListView.as_view()), name='favorite_properties'),
    
    path('property/<int:pk>/descarga/', login_required(PropertyDownloadView.as_view()), name='download_property'), 
        
    path('explorador/mapa/', FinderMapView.as_view(), name='finder'),
    path('explorador/lista/', FinderListView.as_view(), name='finder_without_map'),
    ## Ajax components
    path('finder/purpose/<int:pk>/<slug:klass>/', filter_category_by_purpose, name='finder_by_purpose'),
]