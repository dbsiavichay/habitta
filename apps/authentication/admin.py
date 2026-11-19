from django.conf import settings
from django.contrib import admin
from .models import Profile, SocialProfile, SocialNetwork, SocialNetworkProfile

admin.site.site_header = f'Administración de {settings.SITE_NAME}'
admin.site.site_title = settings.SITE_NAME

class SocialNetworkProfileInline(admin.TabularInline):
	model = SocialNetworkProfile

class ProfileAdmin(admin.ModelAdmin):
	list_display = ('user', 'phone',)
	inlines = [
		SocialNetworkProfileInline,
	]

class SocialProfileAdmin(admin.ModelAdmin):
	list_display = ('identifier', 'provider', 'user',)

class SocialNetworkAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'icon', 'url',)


admin.site.register(Profile, ProfileAdmin)
admin.site.register(SocialProfile, SocialProfileAdmin)
admin.site.register(SocialNetwork, SocialNetworkAdmin)
