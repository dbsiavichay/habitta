import json
from urllib import parse
import requests
from requests_oauthlib import OAuth1
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.contrib.auth.models import User
from .models import SocialProfile

TWITTER_API_KEY = '4Op0tujPygh087slg0kuTU3Wy'
TWITTER_API_SECRET = '8G8FKQxADd6LzFGAQU0gHouuhAYIn8KLDB4XTcUWsnhUJjUhJv'

#FACEBOOK ENGINE
def get_facebook_user(token):
	base_url = 'https://graph.facebook.com/me?fields=%s&access_token=%s'
	fields = 'id,name,first_name,last_name,email,picture'			
	r = requests.get(base_url % (fields, token))
	if r.status_code == 200:
		data = json.loads(r.text)			
		user = get_user_from_social_profile(provider='facebook', identifier=data['id'])

		if not user:
			kwargs = {					
				'username': data.get('id'),
				'first_name': data.get('first_name', ''),
				'last_name': data.get('last_name',''),
				'email': data.get('email', ''),					
				'social': {
					'provider': 'facebook',
					'identifier': data.get('id'),					
					'avatar': data['picture']['data']['url'],
				}
			}
			user = get_or_create_auth_user(**kwargs)

		return user

#TWITTER ENGINE
def get_twitter_authenticate_url():	
	request_token_url = 'https://api.twitter.com/oauth/request_token'
	authenticate_url = 'https://api.twitter.com/oauth/authenticate?oauth_token=%s'		
	auth = OAuth1(TWITTER_API_KEY, TWITTER_API_SECRET)
	r = requests.post(request_token_url, auth=auth)
	if r.status_code == 200:
		data = dict(parse.parse_qsl(r.text))	
		return authenticate_url % data['oauth_token']

def get_twitter_access_token(oauth_token, oauth_verifier):
	access_token_url = 'https://api.twitter.com/oauth/access_token'
	auth = OAuth1(TWITTER_API_KEY, TWITTER_API_SECRET, oauth_token)
	post_data = {'oauth_verifier': oauth_verifier}
	response = requests.post(access_token_url, auth=auth, data=post_data)
	data = dict(parse.parse_qsl(response.text))
	return data

def get_twitter_user(access_token):
	user_url = 'https://api.twitter.com/1.1/account/verify_credentials.json'
	auth = OAuth1(TWITTER_API_KEY, TWITTER_API_SECRET, access_token['oauth_token'], access_token['oauth_token_secret'])
	params = {'include_email': 'true', 'skip_status':'true'}
	r = requests.get(user_url, auth=auth, params=params)
	if r.status_code == 200:
		data = json.loads(r.text)
		user = get_user_from_social_profile(provider='twitter', identifier=data['id'])
		if not user:
			kwargs = {
				'username': data.get('id'),
				'first_name': data.get('name',''),					
				'email': data.get('email',''),	
				'social': {
					'provider': 'twitter',
					'identifier': data.get('id'),
					'avatar': data['profile_image_url'],
				}
			}

			user = get_or_create_auth_user(**kwargs)

		return user

def get_user_from_social_profile(**kwargs):
	try:
		social_profile = SocialProfile.objects.get(provider=kwargs.get('provider'), identifier=kwargs.get('identifier'))
		return social_profile.user
	except SocialProfile.DoesNotExist:
		return

def get_or_create_auth_user(**kwargs):
	try:
		user = User.objects.get(email=kwargs.get('email'))
		return user
	except User.DoesNotExist:
		social_kwargs = kwargs.pop('social')			
		user = User.objects.create_user(**kwargs)
		social_kwargs.update({'user':user})
		resource = requests.get(social_kwargs.pop('avatar'))
		img_temp = NamedTemporaryFile(delete=True)
		img_temp.write(resource.content)
		img_temp.flush()
		user.profile.image.save('%s.jpg' % user.username, File(img_temp), save=True)

		social_profile = SocialProfile.objects.create(**social_kwargs)
		return user