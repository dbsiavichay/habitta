import operator
from functools import reduce

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
from django.db.models import Q
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from apps.realty.models import Property

from . import geocoding
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


class PlacesThrottle(SimpleRateThrottle):
	"""Límite por IP, con o sin sesión: cuida el uso justo del geocodificador."""
	scope = 'places'
	rate = '60/min'

	def get_cache_key(self, request, view):
		return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


def _coordinate(params, name, limit):
	value = _number(params.get(name))
	if value is None or not -limit <= value <= limit:
		raise ValidationError({name: 'Coordenada inválida.'})
	return value


class PlaceSearchAPIView(APIView):
	"""Lugares de Ecuador para el autocompletado (api/geocoding.py).

	Parámetros: q (3 a 120 caracteres); lat y lng opcionales para priorizar lo cercano.
	Respuesta: [{name, detail, label, lat, lng}].
	"""
	throttle_classes = [PlacesThrottle]

	def get(self, request):
		params = request.query_params
		query = ' '.join(params.get('q', '').split())
		if not 3 <= len(query) <= 120:
			raise ValidationError({'q': 'Escribe entre 3 y 120 caracteres.'})
		near = None
		if params.get('lat') or params.get('lng'):
			near = (_coordinate(params, 'lat', 90), _coordinate(params, 'lng', 180))
		return Response(geocoding.search(query, near=near))


class PlaceReverseAPIView(APIView):
	"""Dirección de un punto. Parámetros: lat, lng y zone=1 para sólo «ciudad, provincia».

	Respuesta: {label} (null si no se encontró).
	"""
	throttle_classes = [PlacesThrottle]

	def get(self, request):
		params = request.query_params
		lat = _coordinate(params, 'lat', 90)
		lng = _coordinate(params, 'lng', 180)
		zone = params.get('zone') in ('1', 'true')
		return Response({'label': geocoding.reverse(lat, lng, zone=zone)})
