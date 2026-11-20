"""Búsqueda de lugares y dirección de un punto con Photon (OpenStreetMap).

El navegador no llama a Photon directamente: pasa por /api/places/ (api/views.py), que cachea las
respuestas y permite cambiar de proveedor (Photon autoalojado u otro) sin tocar el frontend.
Ante cualquier error se devuelve una lista vacía o None: el campo queda como texto libre.
"""
import hashlib
import unicodedata

import requests
from django.conf import settings
from django.core.cache import cache

# Ecuador continental y Galápagos: minLon, minLat, maxLon, maxLat
ECUADOR_BBOX = '-92.1,-5.1,-75.1,1.7'
CACHE_SECONDS = 60 * 60 * 24
MAX_RESULTS = 5
# Paradas y estaciones repiten el nombre del barrio o de la ciudad: sólo agregan ruido.
SKIP_TAGS = {
	('highway', 'bus_stop'), ('highway', 'platform'),
	('railway', 'station'), ('railway', 'halt'), ('railway', 'tram_stop'), ('railway', 'subway_entrance'),
}
SKIP_KEYS = {'public_transport'}


def _fold(text):
	"""Minúsculas y sin tildes, para comparar nombres."""
	text = unicodedata.normalize('NFD', text or '')
	return ''.join(c for c in text if not unicodedata.combining(c)).casefold().strip()


def _province(state):
	"""«Provincia de Pichincha» → «Pichincha» (OSM no es consistente)."""
	state = (state or '').strip()
	for prefix in ('Provincia del ', 'Provincia de ', 'Provincia '):
		if state.startswith(prefix):
			return state[len(prefix):]
	return state


def _unique(parts, exclude=()):
	"""Partes no vacías y sin repetir (ignorando tildes y mayúsculas)."""
	seen = {_fold(part) for part in exclude if part}
	result = []
	for part in parts:
		part = (part or '').strip()
		if part and _fold(part) not in seen:
			seen.add(_fold(part))
			result.append(part)
	return result


def _street(props):
	"""Calle con número, si Photon los trae («Av. Amazonas N34-12»)."""
	street = props.get('name') if props.get('type') == 'street' else props.get('street')
	number = props.get('housenumber')
	if street and number and number not in street:
		street = '%s %s' % (street, number)
	return street or ''


def _get(path, params):
	base = (settings.GEOCODER_URL or '').rstrip('/')
	if not base:
		return None
	try:
		response = requests.get(
			base + path, params=params, timeout=settings.EXTERNAL_HTTP_TIMEOUT,
			headers={'User-Agent': settings.GEO_USER_AGENT, 'Accept': 'application/json'},
		)
		response.raise_for_status()
		return response.json()
	except (requests.RequestException, ValueError):
		return None


def _place(feature):
	props = feature.get('properties') or {}
	coords = (feature.get('geometry') or {}).get('coordinates') or []
	if props.get('countrycode') != 'EC' or len(coords) != 2:
		return None
	if props.get('osm_key') in SKIP_KEYS or (props.get('osm_key'), props.get('osm_value')) in SKIP_TAGS:
		return None
	name = (props.get('name') or _street(props)).strip()
	if not name:
		return None
	area = [
		props.get('district') or props.get('locality'),
		props.get('city') or props.get('county'),
		_province(props.get('state')),
	]
	detail = _unique(area, exclude=[name])[:2]
	return {
		'name': name,
		'detail': ', '.join(detail),
		'label': ', '.join([name] + detail),
		'lat': round(coords[1], 6),
		'lng': round(coords[0], 6),
	}


def search(query, near=None):
	"""Hasta 5 lugares de Ecuador para el texto `query`; `near` (lat, lng) prioriza los cercanos.

	Devuelve [{name, detail, label, lat, lng}].
	"""
	query = ' '.join((query or '').split())[:120]
	if len(query) < 3:
		return []
	params = {'q': query, 'limit': 10, 'lang': 'default', 'bbox': ECUADOR_BBOX}
	if near:
		params.update(lat=round(near[0], 2), lon=round(near[1], 2))
	key = 'places:search:' + hashlib.sha1(
		('%s|%s|%s' % (_fold(query), params.get('lat', ''), params.get('lon', ''))).encode()
	).hexdigest()
	cached = cache.get(key)
	if cached is not None:
		return cached

	data = _get('/api/', params)
	if data is None:
		return []  # los errores no se cachean
	places, labels = [], set()
	for feature in data.get('features') or []:
		place = _place(feature)
		if place and _fold(place['label']) not in labels:
			labels.add(_fold(place['label']))
			places.append(place)
		if len(places) == MAX_RESULTS:
			break
	cache.set(key, places, CACHE_SECONDS)
	return places


def reverse(lat, lng, zone=False):
	"""Dirección del punto («Calle, barrio, ciudad») o, con `zone`, sólo «ciudad, provincia»
	(para servicios que atienden una zona). None si no se encuentra."""
	key = 'places:reverse:%s:%.5f,%.5f' % ('zone' if zone else 'exact', lat, lng)
	cached = cache.get(key)
	if cached is not None:
		return cached or None

	data = _get('/reverse', {'lat': lat, 'lon': lng, 'limit': 1, 'lang': 'default'})
	if data is None:
		return None
	features = data.get('features') or []
	props = (features[0].get('properties') or {}) if features else {}
	city = props.get('city') or props.get('county')
	if zone:
		parts = _unique([city or props.get('name'), _province(props.get('state'))])
	else:
		parts = _unique([_street(props), props.get('district') or props.get('locality'), city])
	label = ', '.join(parts)
	cache.set(key, label, CACHE_SECONDS)  # '' también se cachea: punto sin dirección conocida
	return label or None
