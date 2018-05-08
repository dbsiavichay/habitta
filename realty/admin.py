from django.contrib import admin
from .models import Category, Service

class CategoryAdmin(admin.ModelAdmin):
	pass

class ServiceAdmin(admin.ModelAdmin):
	pass

admin.site.register(Category, CategoryAdmin)
admin.site.register(Service, ServiceAdmin)