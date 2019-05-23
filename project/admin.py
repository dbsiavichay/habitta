from django.contrib import admin
from .models import Settings, Icons, Term, Help

class SettingsAdmin(admin.ModelAdmin):
	model = Settings
	list_display = ('title', 'subtitle', 'cover', 'is_active')

	def save_model(self, request, obj, form, change):
		if obj.is_active:
			self.model.objects.all().update(is_active=False)
		super().save_model(request, obj, form, change)

class IconsAdmin(admin.ModelAdmin):
	model = Icons
	list_display = ('name', 'is_active')

	def save_model(self, request, obj, form, change):
		if obj.is_active:
			self.model.objects.all().update(is_active=False)
		super().save_model(request, obj, form, change)

class TermAdmin(admin.ModelAdmin):
	model = Term

class HelpAdmin(admin.ModelAdmin):
	model = Help
	exclude = ('user',)

	def save_model(self, request, obj, form, change):
		obj.user = request.user
		super().save_model(request, obj, form, change)


admin.site.register(Settings, SettingsAdmin)
admin.site.register(Icons, IconsAdmin)
admin.site.register(Term, TermAdmin)
admin.site.register(Help, HelpAdmin)
