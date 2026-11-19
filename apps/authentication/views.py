from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import Http404
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import CreateView, UpdateView, DetailView
from django.contrib.auth import views as auth_views
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.forms import inlineformset_factory
from .models import Profile, SocialNetwork, SocialNetworkProfile
from .forms import (
	UserCreationForm, UserForm, ProfileForm, AvatarForm, CompleteRegisterForm, AuthenticationForm,
	SocialNetworkProfileForm, SocialNetworkProfileFormset
)

from .social import (
	facebook_enabled, twitter_enabled, get_facebook_user,
	get_twitter_authenticate_url, get_twitter_access_token, get_twitter_user
)


def safe_next(request, default=''):
	"""Valor de `next` (POST o GET) sólo si apunta a este mismo sitio."""
	url = request.POST.get('next') or request.GET.get('next') or ''
	if url and url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
		return url
	return default


class UserCreationView(CreateView):
	model = User
	form_class = UserCreationForm
	template_name = 'authentication/register.html'

	def form_valid(self, form):
		self.object = form.save()
		login(self.request, self.object)
		url = reverse('complete_register', args=[self.object.profile.id])
		next_url = safe_next(self.request)
		if next_url:
			url += '?' + urlencode({'next': next_url})
		return redirect(url)

	def get(self, request, *args, **kwargs):
		if request.user.is_authenticated:
			return render(request, template_name = 'authentication/register_yet.html')
		return super().get(request, *args, **kwargs)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['next'] = safe_next(self.request)
		return context

class CompleteRegisterView(UpdateView):
	model = Profile
	form_class = CompleteRegisterForm
	template_name = 'authentication/complete_register.html'

	def get_object(self, queryset=None):
		# Cada usuario sólo puede completar su propio perfil (el pk de la URL se ignora).
		return self.request.user.profile

	def get_success_url(self):
		return safe_next(self.request, reverse('home'))

	def form_valid(self, form):
		response = super().form_valid(form)
		messages.success(self.request, '¡Listo, %s! Tu cuenta ya está completa.' % form.cleaned_data['first_name'])
		return response

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['next'] = self.get_success_url()
		return context

class ProfileUpdateView(UpdateView):
	"""Mi perfil: datos de la cuenta, celular y redes sociales en un solo formulario."""
	model = Profile
	form_class = ProfileForm
	template_name = 'authentication/profile_form.html'
	success_url = reverse_lazy('update_profile')

	def form_valid(self, form):
		user_form = self.get_user_form()
		socialnetworkprofile_formset = self.get_socialnetworkprofile_formset()
		if not all([user_form.is_valid(), socialnetworkprofile_formset.is_valid()]):
			return self.form_invalid(form)

		self.object = form.save()
		user_form.save()

		socialnetworkprofile_formset.instance = self.object
		socialnetworkprofile_formset.save()
		messages.success(self.request, 'Guardamos los cambios de tu perfil.')
		return redirect(self.success_url)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context.update({
			'user_form': self.get_user_form(),
			'socialnetworkprofile_formset': self.get_socialnetworkprofile_formset(),
		})
		return context

	def get_user_form(self):
		if not hasattr(self, '_user_form'):
			post_data = self.request.POST if self.request.method == 'POST' else None
			self._user_form = UserForm(post_data, instance=self.request.user)
		return self._user_form

	def get_socialnetworkprofile_formset(self):
		if hasattr(self, '_socialnetwork_formset'):
			return self._socialnetwork_formset
		post_data = self.request.POST if self.request.method == 'POST' else None
		social_networks = list(SocialNetwork.objects.all())

		Formset = inlineformset_factory(
			Profile, SocialNetworkProfile,
			form = SocialNetworkProfileForm,
			formset = SocialNetworkProfileFormset,
			extra= max(len(social_networks) - self.object.social_networks.count(), 0),
		)
		self._socialnetwork_formset = Formset(post_data, instance=self.object, form_kwargs={'social_networks':social_networks})
		return self._socialnetwork_formset

	def get_object(self, queryset=None):
		return self.request.user.profile

class ProfileUploadImageView(UpdateView):
	"""Cambia la foto de perfil (formulario aparte en Mi perfil) y borra la anterior."""
	model = Profile
	form_class = AvatarForm
	success_url = reverse_lazy('update_profile')

	# Sólo se puede enviar la imagen con POST
	http_method_names = ['post']

	def get_object(self, queryset=None):
		return self.request.user.profile

	def form_valid(self, form):
		previous = Profile.objects.filter(pk=self.object.pk).values_list('image', flat=True).first()
		response = super().form_valid(form)
		if previous and previous != self.object.image.name:
			self.object.image.storage.delete(previous)
		messages.success(self.request, 'Actualizamos tu foto de perfil.')
		return response

	def form_invalid(self, form):
		for error in form.errors.get('image', ['No pudimos usar esa foto.']):
			messages.error(self.request, error)
		return redirect(self.success_url)


class ProfileDetailView(DetailView):
	model = Profile	
	slug_field = 'user__username'
	slug_url_kwarg = 'username'

class LoginView(auth_views.LoginView):
	template_name = 'authentication/login.html'
	form_class = AuthenticationForm

	def get(self, request, *args, **kwargs):
		if not request.user.is_authenticated:
			return super().get(request, *args, **kwargs)
		else:
			return redirect(self.get_success_url())

	def form_valid(self, form):
		response = super().form_valid(form)
		user = form.get_user()
		messages.success(self.request, '¡Hola, %s! Qué bueno verte.' % (user.first_name or user.username))
		return response


class PasswordResetView(auth_views.PasswordResetView):
	template_name = 'authentication/password_reset_form.html'
	subject_template_name = 'authentication/emails/password_reset_subject.txt'
	email_template_name = 'authentication/emails/password_reset_email.txt'
	html_email_template_name = 'authentication/emails/password_reset_email.html'

	@property
	def extra_email_context(self):
		# Sin django.contrib.sites, Django usaría el dominio como nombre del sitio.
		return {
			'site_name': settings.SITE_NAME,
			'site_url': settings.SITE_URL or self.request.build_absolute_uri('/').rstrip('/'),
		}

class SocialLoginView(LoginView):
	def get(self, request, *args, **kwargs):
		# Callback de Twitter (OAuth 1.0a)
		oauth_token = request.GET.get('oauth_token')
		if oauth_token and twitter_enabled():
			access_token = get_twitter_access_token(oauth_token, request.GET.get('oauth_verifier'))
			return self.do_login(get_twitter_user(access_token))
		raise Http404

	def do_login(self, user):
		form = self.get_form()
		if user:
			form.user_cache = user
			return self.form_valid(form)
		return self.form_invalid(form)

	def post(self, request, *args, **kwargs):
		provider = request.POST.get('provider')
		if provider == 'facebook' and facebook_enabled():
			return self.do_login(get_facebook_user(request.POST.get('token')))

		if provider == 'twitter' and twitter_enabled():
			url = get_twitter_authenticate_url()
			if url:
				return redirect(url)

		raise Http404