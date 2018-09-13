from django.contrib import admin
from .models import Specification, Service, Category, Purpose, Property, PropertyImage
from .forms import SpecificationForm

class SpecificationAdmin(admin.ModelAdmin):
	form = SpecificationForm
	
class ServiceAdmin(admin.ModelAdmin):
	pass

class CategoryAdmin(admin.ModelAdmin):
	pass

class PurposeAdmin(admin.ModelAdmin):
	pass

class PropertyImageInline(admin.TabularInline):
    model = PropertyImage

class PropertyAdmin(admin.ModelAdmin):
	inlines = [
		PropertyImageInline,
	]

admin.site.register(Specification, SpecificationAdmin)
admin.site.register(Service, ServiceAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Purpose, PurposeAdmin)
admin.site.register(Property, PropertyAdmin)