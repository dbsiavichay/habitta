from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView
from django.contrib.auth.views import LoginView as AuthLoginView
from django.contrib.auth.models import User
from .models import Profile
from .forms import UserCreationForm, UserForm, ProfileForm, CompleteRegisterForm, AuthenticationForm

from .social import (
	get_facebook_user, 
	get_twitter_authenticate_url, get_twitter_access_token, get_twitter_user
)

class UserCreationView(CreateView):
	model = User
	form_class = UserCreationForm
	template_name = 'authentication/register.html'

	def form_valid(self, form):
		self.object = form.save()
		return redirect(reverse_lazy('complete_register', args=[self.object.profile.id]))

class CompleteRegisterView(UpdateView):
	model = Profile
	form_class = CompleteRegisterForm
	success_url = reverse_lazy('update_profile')
	template_name = 'authentication/complete_register.html'

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

class ProfileDetailView(DetailView):
	model = Profile	
	slug_field = 'user__username'
	slug_url_kwarg = 'username'

class LoginView(AuthLoginView):
	template_name = 'authentication/login.html'
	form_class = AuthenticationForm

	def get(self, request, *args, **kwargs):
		if not request.user.is_authenticated:			
			return super().get(request, *args, **kwargs)
		else:
			return redirect(self.get_success_url())

class SocialLoginView(LoginView):
	def get(self, request, *args, **kwargs):		
		#Only used for twitter
		oauth_token = request.GET.get('oauth_token')		
		if oauth_token:
			access_token = get_twitter_access_token(oauth_token, request.GET.get('oauth_verifier'))
			user = get_twitter_user(access_token)
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
			user = get_facebook_user(request.POST.get('token'))
			return self.do_login(user)

		if provider == 'twitter':
			return redirect(get_twitter_authenticate_url())

	
