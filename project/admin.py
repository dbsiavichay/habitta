from django.contrib import admin
from .models import Settings, Term

class SettingsAdmin(admin.ModelAdmin):
	model = Settings

class TermAdmin(admin.ModelAdmin):
	model = Term


admin.site.register(Term, TermAdmin)
admin.site.register(Settings, SettingsAdmin)
