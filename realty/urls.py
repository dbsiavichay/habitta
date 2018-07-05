from django.urls import path
from .views import (
	ChooseCategoryListView, 
	PropertyListView, PropertyCreateView, PropertyUpdateView, PropertyDetailView,
	PropertyBase64ImageUploadView
)

urlpatterns = [
	path('property/add/', ChooseCategoryListView.as_view(), name='choose_category'),
	path('properties/', PropertyListView.as_view(), name='properties'),
	path('property/add/category/<int:category>/', PropertyCreateView.as_view(), name='add_property'),    	
	path('property/<int:pk>/update/', PropertyUpdateView.as_view(), name='update_property'),    	
	path('property/<int:pk>/detail/', PropertyDetailView.as_view(), name='detail_property'),    	
	path('property/base64image/add/', PropertyBase64ImageUploadView.as_view(), name='add_base64image'),   	
]