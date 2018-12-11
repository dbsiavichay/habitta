from django.contrib import admin
from .models import Settings, Term, Help

class SettingsAdmin(admin.ModelAdmin):
	model = Settings

class TermAdmin(admin.ModelAdmin):
	model = Term

class HelpAdmin(admin.ModelAdmin):
	model = Help


admin.site.register(Term, TermAdmin)
admin.site.register(Settings, SettingsAdmin)
admin.site.register(Help, HelpAdmin)
