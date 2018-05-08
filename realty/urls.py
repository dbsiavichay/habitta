from django.urls import path
from .views import PropertyCreateView, PropertyUpdateView

urlpatterns = [
	path('property/', PropertyCreateView.as_view(), name='add_property'),    	
	path('property/<int:pk>/update/', PropertyUpdateView.as_view(), name='update_property'),    	
]