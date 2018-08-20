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
		queryset = Property.objects.all()

		if not len(self.request.path.split('?')) > 1:
			return queryset

		params = {
			'category': self.request.query_params.get('category', None),
			'purpose': self.request.query_params.get('purpose', None),
			'address__contains': self.request.query_params.get('address', None)
		}

		args = [Q(**{key: params[key]}) for key in params.keys() if params[key] is not None]
		queryset = queryset.filter(reduce(operator.__or__, args))

		return queryset