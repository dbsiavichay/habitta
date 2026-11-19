from django import forms
from django.contrib.auth import forms as auth_forms
from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.models import User
from django.forms.widgets import PasswordInput
from .models import Profile, SocialNetworkProfile

# Resumen de AUTH_PASSWORD_VALIDATORS; el de Django es una lista HTML que no cabe en la ayuda del campo.
PASSWORD_HELP_TEXT = 'Al menos 8 caracteres. Evita contraseñas comunes, sólo números o parecidas a tu usuario.'


class UserCreationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('email', 'username', 'password')
        labels = {
            'email': 'Correo electrónico',
            'username': 'Nombre de usuario',
            'password': 'Contraseña',
        }
        help_texts = {
            'username': 'Será parte de la dirección de tu perfil. Letras, números y @ . + - _, sin espacios.',
            'password': PASSWORD_HELP_TEXT,
        }
        widgets = {
            'email': forms.EmailInput(attrs={'autocomplete': 'email', 'autofocus': True}),
            'username': forms.TextInput(attrs={'autocomplete': 'username', 'autocapitalize': 'none'}),
            'password': PasswordInput(attrs={'autocomplete': 'new-password'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Sin email no hay forma de recuperar la contraseña.
        self.fields['email'].required = True

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('El correo %s ya está asociado a una cuenta.' % email)
        return email

    def _post_clean(self):
        # Igual que el UserCreationForm de Django: se valida tras construir la instancia para que
        # UserAttributeSimilarityValidator compare con el usuario y el email ingresados.
        super()._post_clean()
        password = self.cleaned_data.get('password')
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error('password', error)

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
        for name in ('first_name', 'last_name', 'email'):
            self.fields[name].required = True
        self.fields['first_name'].label = 'Nombres'
        self.fields['last_name'].label = 'Apellidos'
        self.fields['email'].label = 'Correo'
        self.fields['username'].label = 'Usuario'
        self.fields['username'].help_text = 'Aparece en la dirección de tu perfil público. Letras, números y @ . + - _'
        self.fields['first_name'].widget.attrs.update({'autocomplete': 'given-name'})
        self.fields['last_name'].widget.attrs.update({'autocomplete': 'family-name'})
        self.fields['email'].widget.attrs.update({'autocomplete': 'email'})
        self.fields['username'].widget.attrs.update({'autocomplete': 'username'})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        users = User.objects.filter(email=email).exclude(pk=self.instance.pk)

        if email and len(users)>0:
            raise forms.ValidationError('El email %s ya esta asociado a una cuenta.' % email)
        return email

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        exclude = ('user', 'social_networks', 'image')
        labels = {'phone': 'Celular'}
        help_texts = {'phone': 'Lo mostramos en tus anuncios para que te escriban por WhatsApp.'}
        widgets = {'phone': forms.TextInput(attrs={'placeholder': '0991234567', 'inputmode': 'tel', 'autocomplete': 'tel'})}


MAX_AVATAR_BYTES = 5 * 1024 * 1024


class AvatarForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('image',)

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if not image:
            raise forms.ValidationError('Elige una foto.')
        if image.size > MAX_AVATAR_BYTES:
            raise forms.ValidationError('La foto supera el tamaño máximo de 5 MB.')
        return image

class CompleteRegisterForm(ProfileForm):
    first_name = forms.CharField(label='Nombres', max_length=150,
                                 widget=forms.TextInput(attrs={'autocomplete': 'given-name', 'autofocus': True}))
    last_name = forms.CharField(label='Apellidos', max_length=150,
                                widget=forms.TextInput(attrs={'autocomplete': 'family-name'}))

    field_order = ('first_name', 'last_name', 'phone')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Quien entra con una red social ya trae su nombre.
        user = self.instance.user
        self.fields['first_name'].initial = user.first_name
        self.fields['last_name'].initial = user.last_name
        phone = self.fields['phone']
        phone.label = 'Número de celular'
        phone.help_text = 'Para que te contacten por WhatsApp desde tus anuncios.'
        phone.widget.input_type = 'tel'
        phone.widget.attrs.update({'autocomplete': 'tel', 'inputmode': 'tel', 'placeholder': '099 123 4567'})

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.user.first_name = self.cleaned_data.get('first_name')
        profile.user.last_name = self.cleaned_data.get('last_name')
        profile.user.save()

        if commit:
            profile.save()
        return profile


class AuthenticationForm(auth_forms.AuthenticationForm):
    error_messages = {
        'invalid_login': 'El usuario o la contraseña no son correctos. Revisa mayúsculas y minúsculas e inténtalo de nuevo.',
        'inactive': 'Esta cuenta está desactivada.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Correo electrónico o usuario'

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        # Permite entrar con el email; si hay emails duplicados se usa el primero.
        if username and '@' in username:
            user = User.objects.filter(email__iexact=username).order_by('pk').first()
            if user is not None:
                username = user.username

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


class NewPasswordMixin:
    """Etiquetas y ayuda breves para los campos de contraseña nueva."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].help_text = PASSWORD_HELP_TEXT
        self.fields['new_password2'].label = 'Repite la contraseña nueva'
        self.fields['new_password2'].help_text = ''


class SetPasswordForm(NewPasswordMixin, auth_forms.SetPasswordForm):
    pass


class PasswordChangeForm(NewPasswordMixin, auth_forms.PasswordChangeForm):
    error_messages = {
        **auth_forms.PasswordChangeForm.error_messages,
        'password_incorrect': 'Tu contraseña actual no es correcta. Inténtalo de nuevo.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].label = 'Contraseña actual'


class SocialNetworkProfileFormset(forms.BaseInlineFormSet):
    def clean(self):        
        for form in self.forms:
            cleaned_data = form.clean()                     
            id = cleaned_data.get('id', None)
            url = cleaned_data.get('username', None)
            if id and not url:
                cleaned_data['DELETE'] = True
            
        super().clean()         
        
class SocialNetworkProfileForm(forms.ModelForm):
    class Meta:
        model = SocialNetworkProfile
        exclude = ('profile',)
        widgets = {
            'social_network': forms.HiddenInput
        }

    def __init__(self, *args, **kwargs):
        social_networks = kwargs.pop('social_networks', None)
        super().__init__(*args, **kwargs)
        # Vacío en una red ya guardada = quitarla (lo resuelve SocialNetworkProfileFormset.clean)
        self.fields['username'].required = False
        self.fields['username'].widget.attrs.update({'placeholder': 'tu-usuario', 'autocomplete': 'off'})
        self.network = self.instance.social_network if self.instance.pk else None
        if social_networks is None:
            return

        if self.instance.pk is not None:
            for i in range(len(social_networks)):
                if social_networks[i].pk == self.instance.social_network.pk:
                    social_networks.pop(i)
                    break
        elif social_networks:
            self.network = social_networks.pop(0)
            self.fields['social_network'].initial = self.network

    def clean_username(self):
        """Acepta el usuario o el enlace completo y guarda sólo el usuario."""
        username = (self.cleaned_data.get('username') or '').strip()
        prefix = getattr(self.network, 'url', '') or ''
        for candidate in (prefix, prefix.replace('https://', 'http://'), prefix.replace('https://www.', 'https://')):
            if candidate and username.lower().startswith(candidate.lower()):
                username = username[len(candidate):]
                break
        return username.strip('/').lstrip('@')