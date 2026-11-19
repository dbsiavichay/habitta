"""
Login con Facebook y Twitter.

Ambos proveedores están deshabilitados si faltan sus credenciales en el entorno.
"""
import hashlib
import hmac
import logging
from urllib import parse

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from requests_oauthlib import OAuth1

from .models import SocialProfile

logger = logging.getLogger(__name__)

FACEBOOK_GRAPH_URL = 'https://graph.facebook.com/v21.0'


def facebook_enabled():
	return bool(settings.FACEBOOK_APP_ID and settings.FACEBOOK_APP_SECRET)


def twitter_enabled():
	return bool(settings.TWITTER_API_KEY and settings.TWITTER_API_SECRET)


def _get(url, **kwargs):
	kwargs.setdefault('timeout', settings.EXTERNAL_HTTP_TIMEOUT)
	return requests.get(url, **kwargs)


def _post(url, **kwargs):
	kwargs.setdefault('timeout', settings.EXTERNAL_HTTP_TIMEOUT)
	return requests.post(url, **kwargs)


# FACEBOOK
def _facebook_token_is_ours(token):
	"""Verifica que el token sea válido y emitido para NUESTRA app (evita sustitución de tokens)."""
	app_token = f'{settings.FACEBOOK_APP_ID}|{settings.FACEBOOK_APP_SECRET}'
	r = _get(f'{FACEBOOK_GRAPH_URL}/debug_token', params={'input_token': token, 'access_token': app_token})
	if r.status_code != 200:
		return False
	data = r.json().get('data', {})
	return bool(data.get('is_valid')) and str(data.get('app_id')) == str(settings.FACEBOOK_APP_ID)


def get_facebook_user(token):
	if not facebook_enabled() or not token:
		return None
	try:
		if not _facebook_token_is_ours(token):
			logger.warning('Token de Facebook inválido o de otra aplicación')
			return None
		proof = hmac.new(settings.FACEBOOK_APP_SECRET.encode(), token.encode(), hashlib.sha256).hexdigest()
		r = _get(f'{FACEBOOK_GRAPH_URL}/me', params={
			'fields': 'id,name,first_name,last_name,email,picture',
			'access_token': token,
			'appsecret_proof': proof,
		})
	except requests.RequestException:
		logger.exception('Error consultando Facebook')
		return None
	if r.status_code != 200:
		return None

	data = r.json()
	user = get_user_from_social_profile(provider='facebook', identifier=data.get('id'))
	if user:
		return user
	return create_social_user(
		username=data.get('id'),
		first_name=data.get('first_name', ''),
		last_name=data.get('last_name', ''),
		email=data.get('email', ''),
		provider='facebook',
		identifier=data.get('id'),
		avatar=data.get('picture', {}).get('data', {}).get('url'),
	)


# TWITTER (OAuth 1.0a)
def get_twitter_authenticate_url():
	if not twitter_enabled():
		return None
	auth = OAuth1(settings.TWITTER_API_KEY, settings.TWITTER_API_SECRET)
	try:
		r = _post('https://api.twitter.com/oauth/request_token', auth=auth)
	except requests.RequestException:
		logger.exception('Error consultando Twitter')
		return None
	if r.status_code == 200:
		data = dict(parse.parse_qsl(r.text))
		return 'https://api.twitter.com/oauth/authenticate?oauth_token=%s' % data['oauth_token']
	return None


def get_twitter_access_token(oauth_token, oauth_verifier):
	auth = OAuth1(settings.TWITTER_API_KEY, settings.TWITTER_API_SECRET, oauth_token)
	response = _post('https://api.twitter.com/oauth/access_token', auth=auth, data={'oauth_verifier': oauth_verifier})
	return dict(parse.parse_qsl(response.text))


def get_twitter_user(access_token):
	if not twitter_enabled() or 'oauth_token' not in access_token:
		return None
	auth = OAuth1(
		settings.TWITTER_API_KEY, settings.TWITTER_API_SECRET,
		access_token['oauth_token'], access_token['oauth_token_secret'],
	)
	try:
		r = _get(
			'https://api.twitter.com/1.1/account/verify_credentials.json',
			auth=auth, params={'include_email': 'true', 'skip_status': 'true'},
		)
	except requests.RequestException:
		logger.exception('Error consultando Twitter')
		return None
	if r.status_code != 200:
		return None

	data = r.json()
	user = get_user_from_social_profile(provider='twitter', identifier=data['id'])
	if user:
		return user
	return create_social_user(
		username=data.get('id'),
		first_name=data.get('name', ''),
		email=data.get('email', ''),
		provider='twitter',
		identifier=data.get('id'),
		avatar=data.get('profile_image_url'),
	)


# Usuarios
def get_user_from_social_profile(**kwargs):
	social_profile = SocialProfile.objects.filter(**kwargs).select_related('user').first()
	return social_profile.user if social_profile else None


def create_social_user(provider, identifier, avatar=None, **user_kwargs):
	"""Crea un usuario nuevo vinculado a una red social.

	No se vincula automáticamente a una cuenta existente con el mismo email:
	eso permitiría tomar el control de cuentas ajenas con un email no verificado.
	"""
	email = user_kwargs.get('email')
	if email and User.objects.filter(email__iexact=email).exists():
		logger.info('Login social rechazado: ya existe una cuenta con el email de %s', provider)
		return None

	user = User.objects.create_user(**user_kwargs)
	SocialProfile.objects.create(provider=provider, identifier=identifier, user=user)

	if avatar:
		try:
			resource = _get(avatar)
			if resource.status_code == 200:
				user.profile.image.save('%s.jpg' % user.username, ContentFile(resource.content), save=True)
		except requests.RequestException:
			logger.warning('No se pudo descargar el avatar de %s', provider)
	return user
