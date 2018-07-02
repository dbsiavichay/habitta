from django.contrib import admin
from .models import Specification, Service, Category, Purpose, Property

class SpecificationAdmin(admin.ModelAdmin):
	class Media:
		css = {
			'all':('plugins/fontawesome/fontawesome.min.css',),
		}

class ServiceAdmin(admin.ModelAdmin):
	pass

class CategoryAdmin(admin.ModelAdmin):
	pass

class PurposeAdmin(admin.ModelAdmin):
	pass

class PropertyAdmin(admin.ModelAdmin):
	pass

admin.site.register(Specification, SpecificationAdmin)
admin.site.register(Service, ServiceAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Purpose, PurposeAdmin)
admin.site.register(Property, PropertyAdmin)