from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.views import LoginView as AuthLoginView
from django.contrib.auth.models import User
from .models import Profile, SocialProfile
from .forms import UserCreationForm, UserForm, ProfileForm, CompleteRegisterForm, AuthenticationForm
# imports for social login
import json
from urllib import parse
import requests
from requests_oauthlib import OAuth1
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile

class UserCreationView(CreateView):
	model = User
	form_class = UserCreationForm
	template_name = 'authentication/register.html'

	def form_valid(self, form):
		self.object = form.save()
		return redirect(reverse_lazy('complete_register', args=[self.object.profile.id]))

class ProfileUpdateView(UpdateView):
	model = Profile
	form_class = ProfileForm
	success_url = reverse_lazy('update_profile')

	def form_valid(self, form):
		user_form = self.get_user_form()
		if not user_form.is_valid():
			return self.form_invalid(form)

		self.object = form.save()
		user_form.save()
		
		return redirect(self.success_url)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)		
		context.update({'user_form': self.get_user_form()})
		return context

	def get_user_form(self):
		post_data = self.request.POST if self.request.method == 'POST' else None		
		form = UserForm(post_data, instance=self.request.user)
		return form

	def get_object(self, queryset=None):		
		return self.request.user.profile

class ProfileUploadImageView(UpdateView):
	model = Profile
	fields = ('image',)
	success_url = reverse_lazy('update_profile')

	def get_object(self, queryset=None):		
		return self.request.user.profile

	def get(self, request, *args, **kwargs):
		# Solo se puede enviar la imagen con post acción no permitida en get
		return 'Acción no permitida'

class CompleteRegisterView(UpdateView):
	model = Profile
	form_class = CompleteRegisterForm
	success_url = reverse_lazy('update_profile')
	template_name = 'authentication/complete_register.html'

class LoginView(AuthLoginView):
	template_name = 'authentication/login.html'
	form_class = AuthenticationForm

class SocialLoginView(LoginView):
	twitter_api_key = '4Op0tujPygh087slg0kuTU3Wy'
	twitter_api_secret = '8G8FKQxADd6LzFGAQU0gHouuhAYIn8KLDB4XTcUWsnhUJjUhJv'

	def get(self, request, *args, **kwargs):		
		#Only used for twitter
		oauth_token = request.GET.get('oauth_token')
		access_token_url = 'https://api.twitter.com/oauth/access_token'
		
		if oauth_token:
			access_token = self.get_twitter_access_token(oauth_token, request.GET.get('oauth_verifier'))
			user = self.get_twitter_user(access_token)
			return self.do_login(user)

		return '404'

	def do_login(self, user):
		form = self.get_form()		
		if user:
			form.user_cache = user		
			return self.form_valid(form)
		else:
			return self.form_invalid(form)

	def post(self, request, *args, **kwargs):		
		provider = request.POST.get('provider')
		if provider == 'facebook':
			user = self.get_facebook_user(request.POST.get('token'))
			return self.do_login(user)

		if provider == 'twitter':
			return redirect(self.get_twitter_authenticate_url())

	def get_facebook_user(self, token):
		base_url = 'https://graph.facebook.com/me?fields=%s&access_token=%s'
		fields = 'id,name,first_name,last_name,email,picture'			
		r = requests.get(base_url % (fields, token))
		if r.status_code == 200:
			data = json.loads(r.text)			
			user = self.get_user_from_social_profile(provider='facebook', identifier=data['id'])

			if not user:
				kwargs = {					
					'username': data['id'],
					'first_name': data['first_name'],
					'last_name': data['last_name'],
					'email': data.get('email', ''),					
					'social': {
						'provider': 'facebook',
						'identifier': data['id'],					
						'avatar': data['picture']['data']['url'],
					}
				}
				user = self.get_or_create_auth_user(**kwargs)

			return user

	def get_twitter_authenticate_url(self):
		request_token_url = 'https://api.twitter.com/oauth/request_token'
		authenticate_url = 'https://api.twitter.com/oauth/authenticate?oauth_token=%s'		
		auth = OAuth1(self.twitter_api_key, self.twitter_api_secret)
		r = requests.post(request_token_url, auth=auth)
		if r.status_code == 200:
			data = dict(parse.parse_qsl(r.text))	
			return authenticate_url % data['oauth_token']

	def get_twitter_access_token(self, oauth_token, oauth_verifier):
		access_token_url = 'https://api.twitter.com/oauth/access_token'
		auth = OAuth1(self.twitter_api_key, self.twitter_api_secret, oauth_token)
		post_data = {'oauth_verifier': oauth_verifier}
		response = requests.post(access_token_url, auth=auth, data=post_data)
		data = dict(parse.parse_qsl(response.text))
		return data

	def get_twitter_user(self, access_token):
		user_url = 'https://api.twitter.com/1.1/account/verify_credentials.json'
		auth = OAuth1(self.twitter_api_key, self.twitter_api_secret, access_token['oauth_token'], access_token['oauth_token_secret'])
		params = {'include_email': 'true', 'skip_status':'true'}
		r = requests.get(user_url, auth=auth, params=params)
		if r.status_code == 200:
			data = json.loads(r.text)
			user = self.get_user_from_social_profile(provider='twitter', identifier=data['id'])
			if not user:
				kwargs = {
					'username': data['id'],
					'first_name': data['name'],					
					'email': data.get('email',''),	
					'social': {
						'provider': 'twitter',
						'identifier': data['id'],
						'avatar': data['profile_image_url'],
					}
				}

				user = self.get_or_create_auth_user(**kwargs)

			return user

	def get_user_from_social_profile(self, **kwargs):
		try:
			social_profile = SocialProfile.objects.get(provider=kwargs.get('provider'), identifier=kwargs.get('identifier'))
			return social_profile.user
		except SocialProfile.DoesNotExist:
			return

	def get_or_create_auth_user(self, **kwargs):
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
