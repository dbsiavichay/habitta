from rest_framework import generics
from .serializers import PropertySerializer
from apps.realty.models import Property
from django.db.models import Q
from functools import reduce

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
import operator

class PropertyListAPIView(generics.ListAPIView):
	#queryset = Property.objects.all()
	serializer_class = PropertySerializer

	def get_queryset(self):      
		#queryset = Property.objects.exclude(category__require_location=False)
		queryset = Property.objects.all()
		lat = self.request.query_params.get('lat', None)
		lng = self.request.query_params.get('lng', None)
		radio = self.request.query_params.get('radio', None)
		min_price = self.request.query_params.get('min_price', None)
		max_price = self.request.query_params.get('max_price', None)
		purpose = self.request.query_params.get('purpose', None)
		address = self.request.query_params.get('address', None)

		if lat and lng:
			point = Point(float(lng), float(lat))
			queryset = queryset.exclude(category__require_location=False).filter(geopoint__distance_lte=(point, Distance(km=int(radio))))
			queryset = queryset | Property.objects.filter(category__require_location=False)
		
		params = {
			'category': self.request.query_params.get('category', None),
			'details__purpose': int(purpose) if purpose else purpose,
			'address__icontains': address
		}		
		args = [Q(**{key: params[key]}) for key in params.keys() if params[key] is not None]

		count_args = 0
		for arg in args:
			count_args+=1
	
		if count_args:		
			queryset = queryset.filter(reduce(operator.__and__, args))

		if min_price and max_price:
			min_price = float(min_price)
			max_price = float(max_price)
			queryset = [obj for obj in queryset if isinstance(obj.get_price_area(), float)]
			queryset = [obj for obj in queryset if min_price <= float(obj.get_price_area()) <= max_price]
		return queryset