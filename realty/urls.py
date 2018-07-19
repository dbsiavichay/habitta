from django.urls import path
from django.contrib.auth.decorators import login_required
from .views import (
	ChooseCategoryListView, 
	PropertyListView, PropertyCreateView, PropertyUpdateView, PropertyDetailView,
	PropertyBase64ImageUploadView,
	FinderListView,
)

urlpatterns = [
	path('property/add/', login_required(ChooseCategoryListView.as_view()), name='choose_category'),
	path('properties/', login_required(PropertyListView.as_view()), name='properties'),
	path('property/add/category/<int:category>/', login_required(PropertyCreateView.as_view()), name='add_property'),    	
	path('property/<int:pk>/update/', login_required(PropertyUpdateView.as_view()), name='update_property'),    	
	path('property/<int:pk>/detail/', login_required(PropertyDetailView.as_view()), name='detail_property'),    	
	path('property/base64image/add/', login_required(PropertyBase64ImageUploadView.as_view()), name='add_base64image'),

	path('finder/', FinderListView.as_view(), name='finder'),
]