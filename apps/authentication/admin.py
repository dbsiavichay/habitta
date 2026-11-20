from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from unfold.admin import ModelAdmin, TabularInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import Profile, SocialNetwork, SocialProfile, SocialNetworkProfile

# El título y la marca del admin los da UNFOLD (config/unfold.py).

# User y Group vienen registrados por django.contrib.auth con el admin de serie: se vuelven a
# registrar con los formularios de Unfold para que tengan el mismo estilo.
admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
	form = UserChangeForm
	add_form = UserCreationForm
	change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
	pass


class SocialNetworkProfileInline(TabularInline):
	model = SocialNetworkProfile


@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
	list_display = ('user', 'phone',)
	inlines = [
		SocialNetworkProfileInline,
	]


@admin.register(SocialProfile)
class SocialProfileAdmin(ModelAdmin):
	list_display = ('identifier', 'provider', 'user',)


@admin.register(SocialNetwork)
class SocialNetworkAdmin(ModelAdmin):
	list_display = ('id', 'name', 'icon', 'url',)
