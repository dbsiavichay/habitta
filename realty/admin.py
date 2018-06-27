from django.contrib import admin
from .models import Specification, Service, Category, Purpose

class SpecificationAdmin(admin.ModelAdmin):
	pass

class ServiceAdmin(admin.ModelAdmin):
	pass

class CategoryAdmin(admin.ModelAdmin):
	pass

class PurposeAdmin(admin.ModelAdmin):
	pass

admin.site.register(Specification, SpecificationAdmin)
admin.site.register(Service, ServiceAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Purpose, PurposeAdmin)