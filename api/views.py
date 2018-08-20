from rest_framework import generics
from .serializers import PropertySerializer
from realty.models import Property

class PropertyListAPIView(generics.ListAPIView):
	queryset = Property.objects.all()
	serializer_class = PropertySerializer
