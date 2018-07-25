from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.views import LoginView as AuthLoginView
from django.contrib.auth.models import User
from .models import Profile
from .forms import UserCreationForm, UserForm, ProfileForm, CompleteRegisterForm, AuthenticationForm

from django.contrib.auth import login

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
	def get(self, request, *args, **kwargs):
		import requests
		import json
		from django.core.files import File
		from django.core.files.temp import NamedTemporaryFile		
		base_url = 'https://graph.facebook.com/me?fields=id,name,first_name,last_name,email,picture&access_token=%s'			
		r = requests.get(base_url % kwargs.get('token'))
		if r.status_code == 200:
			data = json.loads(r.text)
			print(data)
			try:
				user = User.objects.get(email=data['email'])
			except User.DoesNotExist:
				user_kwargs = {
					'username': data['id'],
					'first_name': data['first_name'],
					'last_name': data['last_name'],
					'email': data['email']
				}
				user = User.objects.create_user(**user_kwargs)
				r = requests.get(data['picture']['data']['url'])
				img_temp = NamedTemporaryFile(delete=True)
				img_temp.write(r.content)
				img_temp.flush()

				user.profile.image.save('%s.jpg' % user.username, File(img_temp), save=True)

			login(request, user)
			next = request.GET.get('next')
			next = next if next else 'home'

			return redirect(next)





	