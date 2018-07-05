from django import forms
from django.contrib.auth.models import User
from .models import Profile

class UserCreationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('email', 'username', 'password')

    def clean_email(self):
        email = self.cleaned_data.get("email")
        users = User.objects.filter(email=email)

        if email and len(users)>0:
            raise forms.ValidationError('El email %s ya esta asociado a una cuenta.' % email)
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()

        return user