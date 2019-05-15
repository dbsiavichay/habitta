from rest_framework import generics
from .serializers import PropertySerializer
from realty.models import Property
from django.db.models import Q
from functools import reduce
import operator

class PropertyListAPIView(generics.ListAPIView):
	#queryset = Property.objects.all()
	serializer_class = PropertySerializer

	def get_queryset(self):        
		queryset = Property.objects.exclude(category__require_location=False)

		if len(self.request.query_params) == 0:		
			return queryset

		purpose = self.request.query_params.get('purpose', None)

		params = {
			'category': self.request.query_params.get('category', None),
			'details__purpose': int(purpose) if purpose else purpose,
			'address__icontains': self.request.query_params.get('address', None)
		}		
		
		args = [Q(**{key: params[key]}) for key in params.keys() if params[key] is not None]
		queryset = queryset.filter(reduce(operator.__and__, args))

		return queryset