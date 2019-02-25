from django.urls import path
from django.contrib.auth.decorators import login_required
from authentication.decorators import owner_required
from .views import (
	ChooseCategoryListView, 
	PropertyListView, PropertyCreateView, PropertyUpdateView, PropertyDetailView,
	PropertyBase64ImageUploadView, PropertyImageDeleteView,
	PropertyFavoriteListView, PropertyDownloadView,
	FinderListView,
)

urlpatterns = [
	path('property/add/', login_required(ChooseCategoryListView.as_view()), name='choose_category'),
	path('properties/', login_required(PropertyListView.as_view()), name='properties'),
	path('property/add/category/<int:category>/', login_required(PropertyCreateView.as_view()), name='add_property'),    	
	path('property/<int:pk>/update/', owner_required(PropertyUpdateView.as_view()), name='update_property'),    		
	path('property/base64image/add/', login_required(PropertyBase64ImageUploadView.as_view()), name='add_property_base64image'),
	path('property/image/<int:pk>/delete/', login_required(PropertyImageDeleteView.as_view()), name='delete_property_image'),	
	path('property/<int:pk>/detail/', PropertyDetailView.as_view(), name='detail_property'),    	
	path('favorite/properties/', login_required(PropertyFavoriteListView.as_view()), name='favorite_properties'),
	path('property/<int:pk>/download/', PropertyDownloadView.as_view(), name='download_property'),    		
	
	path('finder/', FinderListView.as_view(), name='finder'),
]