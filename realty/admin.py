from django.contrib import admin
from .models import Specification, Service, Category, Purpose, Property, PropertyImage, Group, GroupCategory
from .forms import SpecificationForm, CategoryForm

class SpecificationAdmin(admin.ModelAdmin):
	form = SpecificationForm
	list_display = ['name', 'internal_name', 'is_required', 'order',]

class GroupAdmin(admin.ModelAdmin):
	pass
	
class ServiceAdmin(admin.ModelAdmin):
	pass

class GroupCategoryInline(admin.TabularInline):
	model = GroupCategory

class CategoryAdmin(admin.ModelAdmin):
	form = CategoryForm
	list_display = ['name', 'singular_name', 'order']
	inlines = [
		GroupCategoryInline,
	]

class PurposeAdmin(admin.ModelAdmin):
	pass

class PropertyImageInline(admin.TabularInline):
    model = PropertyImage

class PropertyAdmin(admin.ModelAdmin):
	list_display = ('price', 'description', 'address', 'pub_date')
	inlines = [
		PropertyImageInline,
	]

admin.site.register(Specification, SpecificationAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(Service, ServiceAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Purpose, PurposeAdmin)
admin.site.register(Property, PropertyAdmin)