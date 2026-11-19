import operator
from functools import reduce

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
from django.db.models import Q
from rest_framework import generics

from apps.realty.models import Property

from .serializers import PropertySerializer


def _number(value, cast=float):
	"""Convierte un parámetro de la URL; devuelve None si falta o no es válido (en vez de un error 500)."""
	try:
		return cast(value) if value not in (None, '') else None
	except (TypeError, ValueError):
		return None


class PropertyListAPIView(generics.ListAPIView):
	"""Anuncios para el explorador (mapa y lista).

	Parámetros: lat, lng, radio (km), kind (1 inmuebles, 2 servicios, 3 empleos), category,
	purpose, address (texto), min_price, max_price.
	"""
	serializer_class = PropertySerializer

	def get_queryset(self):
		params = self.request.query_params
		queryset = Property.objects.select_related('category', 'user__profile')
		lat = _number(params.get('lat'))
		lng = _number(params.get('lng'))
		radio = _number(params.get('radio'), int) or 15
		min_price = _number(params.get('min_price'))
		max_price = _number(params.get('max_price'))
		purpose = _number(params.get('purpose'), int)
		category = _number(params.get('category'), int)
		kind = _number(params.get('kind'), int)
		address = params.get('address') or None

		if lat is not None and lng is not None:
			point = Point(lng, lat)
			# Los servicios sin ubicación fija (áreas de operación) aparecen siempre.
			queryset = queryset.filter(
				Q(category__require_location=True, geopoint__distance_lte=(point, Distance(km=radio)))
				| Q(category__require_location=False)
			)

		filters = {
			'category': category,
			'category__kind': kind,
			'details__purpose': purpose,
			'address__icontains': address,
		}
		args = [Q(**{key: value}) for key, value in filters.items() if value is not None]
		if args:
			queryset = queryset.filter(reduce(operator.and_, args))

		if min_price is not None or max_price is not None:
			low = min_price if min_price is not None else 0
			high = max_price if max_price is not None else float('inf')
			# El precio vive en el JSON de especificaciones: se filtra en Python.
			queryset = [obj for obj in queryset if (price := obj.get_price_value()) is not None and low <= price <= high]
		return queryset
