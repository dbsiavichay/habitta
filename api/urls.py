from django.urls import include, path
from .views import PropertyListAPIView

urlpatterns = [
	path('auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('properties/', PropertyListAPIView.as_view()),
]