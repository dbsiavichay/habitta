from unittest.mock import MagicMock, patch

import requests
from django.core.cache import cache
from django.test import TestCase, override_settings


def photon(*features):
	response = MagicMock()
	response.json.return_value = {'type': 'FeatureCollection', 'features': list(features)}
	return response


def feature(lng, lat, **props):
	props.setdefault('countrycode', 'EC')
	return {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [lng, lat]}, 'properties': props}


LA_CAROLINA = feature(
	-78.4844205, -0.1831335, type='district', osm_key='place', osm_value='suburb', name='La Carolina',
	county='Quito', state='Pichincha',
)
STATION = feature(
	-78.4855008, -0.190368, type='house', osm_key='railway', osm_value='station', name='La Carolina',
	district='La Carolina', city='Quito', state='Pichincha',
)
PERU = feature(-77.76, -4.49, type='street', osm_key='highway', osm_value='residential', name='Av. Amazonas', countrycode='PE')
STREET = feature(
	-78.490727, -0.1994356, type='street', osm_key='highway', osm_value='tertiary', name='Avenida Río Amazonas',
	district='Mariscal Sucre', city='Quito', county='Quito', state='Provincia de Pichincha',
)


@override_settings(GEOCODER_URL='https://photon.test', GEO_USER_AGENT='Habitta-tests/1.0')
class PlaceSearchTests(TestCase):
	url = '/api/places/'

	def setUp(self):
		cache.clear()

	def test_maps_photon_results_to_places_of_ecuador(self):
		with patch('api.geocoding.requests.get', return_value=photon(STATION, LA_CAROLINA, PERU, STREET)) as get:
			response = self.client.get(self.url, {'q': 'La Carolina'})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json(), [
			{'name': 'La Carolina', 'detail': 'Quito, Pichincha', 'label': 'La Carolina, Quito, Pichincha', 'lat': -0.183134, 'lng': -78.48442},
			{'name': 'Avenida Río Amazonas', 'detail': 'Mariscal Sucre, Quito', 'label': 'Avenida Río Amazonas, Mariscal Sucre, Quito', 'lat': -0.199436, 'lng': -78.490727},
		])  # sin la estación (repite el barrio) ni el resultado de Perú
		args, kwargs = get.call_args
		self.assertEqual(args[0], 'https://photon.test/api/')
		self.assertEqual(kwargs['params']['bbox'], '-92.1,-5.1,-75.1,1.7')
		self.assertEqual(kwargs['headers']['User-Agent'], 'Habitta-tests/1.0')

	def test_results_are_cached(self):
		with patch('api.geocoding.requests.get', return_value=photon(LA_CAROLINA)) as get:
			self.client.get(self.url, {'q': 'La Carolina'})
			response = self.client.get(self.url, {'q': '  la carolina '})
		self.assertEqual(get.call_count, 1)
		self.assertEqual(response.json()[0]['name'], 'La Carolina')

	def test_near_biases_the_search(self):
		with patch('api.geocoding.requests.get', return_value=photon(LA_CAROLINA)) as get:
			self.client.get(self.url, {'q': 'Carolina', 'lat': '-0.18', 'lng': '-78.48'})
		params = get.call_args.kwargs['params']
		self.assertEqual((params['lat'], params['lon']), (-0.18, -78.48))

	def test_errors_return_an_empty_list_and_are_not_cached(self):
		with patch('api.geocoding.requests.get', side_effect=requests.Timeout):
			response = self.client.get(self.url, {'q': 'Quito'})
		self.assertEqual(response.json(), [])
		with patch('api.geocoding.requests.get', return_value=photon(LA_CAROLINA)) as get:
			self.client.get(self.url, {'q': 'Quito'})
		get.assert_called_once()

	@override_settings(GEOCODER_URL='')
	def test_disabled_geocoder_returns_nothing(self):
		with patch('api.geocoding.requests.get') as get:
			response = self.client.get(self.url, {'q': 'Quito'})
		self.assertEqual(response.json(), [])
		get.assert_not_called()

	def test_invalid_parameters(self):
		with patch('api.geocoding.requests.get') as get:
			self.assertEqual(self.client.get(self.url, {'q': 'ab'}).status_code, 400)
			self.assertEqual(self.client.get(self.url, {'q': 'x' * 121}).status_code, 400)
			self.assertEqual(self.client.get(self.url, {'q': 'Quito', 'lat': '95', 'lng': '-78'}).status_code, 400)
		get.assert_not_called()


@override_settings(GEOCODER_URL='https://photon.test')
class PlaceReverseTests(TestCase):
	url = '/api/places/reverse/'
	point = feature(
		-78.4838876, -0.1798612, type='house', osm_key='tourism', osm_value='attraction',
		name='Avión del Parque La Carolina', street='Japón', housenumber='N35-12', locality='La Carolina',
		district='La Carolina', city='Quito', county='Quito', state='Pichincha',
	)

	def setUp(self):
		cache.clear()

	def test_exact_address(self):
		with patch('api.geocoding.requests.get', return_value=photon(self.point)) as get:
			response = self.client.get(self.url, {'lat': '-0.1807', 'lng': '-78.4842'})
		self.assertEqual(response.json(), {'label': 'Japón N35-12, La Carolina, Quito'})
		self.assertEqual(get.call_args.args[0], 'https://photon.test/reverse')

	def test_zone_for_services(self):
		with patch('api.geocoding.requests.get', return_value=photon(self.point)):
			response = self.client.get(self.url, {'lat': '-0.1807', 'lng': '-78.4842', 'zone': '1'})
		self.assertEqual(response.json(), {'label': 'Quito, Pichincha'})

	def test_nothing_found(self):
		with patch('api.geocoding.requests.get', return_value=photon()):
			response = self.client.get(self.url, {'lat': '-0.1807', 'lng': '-78.4842'})
		self.assertEqual(response.json(), {'label': None})

	def test_invalid_coordinates(self):
		self.assertEqual(self.client.get(self.url, {'lat': 'x', 'lng': '-78'}).status_code, 400)
		self.assertEqual(self.client.get(self.url, {'lat': '-0.18'}).status_code, 400)
		self.assertEqual(self.client.get(self.url, {'lat': '-0.18', 'lng': '200'}).status_code, 400)
