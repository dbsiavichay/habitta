from django import forms
from django.contrib.auth.forms import AuthenticationForm as AuthAuthenticationForm
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.forms.widgets import PasswordInput
from .models import Profile

class UserCreationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('email', 'username', 'password')
        widgets = {
            'password': PasswordInput
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        users = User.objects.filter(email=email)

        if email and len(users)>0:
            raise forms.ValidationError('El email %s ya esta asociado a una cuenta.' % email)
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()

        return user

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].require = True
        self.fields['last_name'].require = True        
        self.fields['email'].require = True        

    def clean_email(self):
        email = self.cleaned_data.get('email')
        users = User.objects.filter(email=email).exclude(pk=self.instance.pk)

        if email and len(users)>0:
            raise forms.ValidationError('El email %s ya esta asociado a una cuenta.' % email)
        return email

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        exclude = ('user',)    

class CompleteRegisterForm(ProfileForm):
    first_name = forms.CharField(label='Nombres')
    last_name = forms.CharField(label='Apellidos')    

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.user.first_name = self.cleaned_data.get('first_name')
        profile.user.last_name = self.cleaned_data.get('last_name')
        profile.user.save()

        if commit:
            profile.save()
        return profile


class AuthenticationForm(AuthAuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Nombre de usuario o correo electrónico'

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        try:
            user = User.objects.get(email=username)
            username = user.username
        except User.DoesNotExist:
            pass

        if username is not None and password:
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'username': self.username_field.verbose_name},
                )
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data