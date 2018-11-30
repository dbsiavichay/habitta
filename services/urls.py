from django.urls import path
from .views import ServiceListView, UserServiceListView, UserServiceCreateView, UserServiceUpdateView

urlpatterns = [
	path('', ServiceListView.as_view(), name='services'),	
	path('services/', UserServiceListView.as_view(), name='user_services'),	
	path('service/add/', UserServiceCreateView.as_view(), name='add_service'),	
	path('service/<int:pk>/update/', UserServiceUpdateView.as_view(), name='update_service'),	
]