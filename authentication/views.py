from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.views import LoginView as AuthLoginView
from django.contrib.auth.models import User
from .models import Profile
from .forms import UserCreationForm, ProfileForm, AuthenticationForm

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
	success_url = reverse_lazy('home')

class CompleteRegisterView(ProfileUpdateView):
	template_name = 'authentication/complete_register.html'

class LoginView(AuthLoginView):
	template_name = 'authentication/login.html'
	form_class = AuthenticationForm


	