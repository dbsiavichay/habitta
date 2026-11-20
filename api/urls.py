from django.urls import include, path
from .views import PlaceReverseAPIView, PlaceSearchAPIView, PropertyListAPIView

urlpatterns = [
	path('auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('properties/', PropertyListAPIView.as_view()),
    path('places/', PlaceSearchAPIView.as_view()),
    path('places/reverse/', PlaceReverseAPIView.as_view()),
]