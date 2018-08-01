from django.contrib import admin
from .models import Profile, SocialProfile

class ProfileAdmin(admin.ModelAdmin):
	pass

class SocialProfileAdmin(admin.ModelAdmin):
	pass


admin.site.register(Profile, ProfileAdmin)
admin.site.register(SocialProfile, SocialProfileAdmin)
