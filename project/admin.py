from django.contrib import admin
from .models import Settings, Term, Help

class SettingsAdmin(admin.ModelAdmin):
	model = Settings

class TermAdmin(admin.ModelAdmin):
	model = Term

class HelpAdmin(admin.ModelAdmin):
	model = Help
	exclude = ('user',)

	def save_model(self, request, obj, form, change):
		obj.user = request.user
		super().save_model(request, obj, form, change)


admin.site.register(Term, TermAdmin)
admin.site.register(Settings, SettingsAdmin)
admin.site.register(Help, HelpAdmin)
