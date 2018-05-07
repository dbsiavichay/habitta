from django.urls import path
from .views import PropertyCreateView

urlpatterns = [
	path('property/', PropertyCreateView.as_view(), name='add_property'),    	
]