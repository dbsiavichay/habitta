from django.contrib import admin
from .models import Profile, SocialProfile, SocialNetwork

class ProfileAdmin(admin.ModelAdmin):
	list_display = ('user', 'phone', 'website',)

class SocialProfileAdmin(admin.ModelAdmin):
	list_display = ('identifier', 'provider', 'user',)

class SocialNetworkAdmin(admin.ModelAdmin):
	list_display = ('name', 'icon', 'url',)


admin.site.register(Profile, ProfileAdmin)
admin.site.register(SocialProfile, SocialProfileAdmin)
admin.site.register(SocialNetwork, SocialNetworkAdmin)
