from django.contrib import admin
from .models import Specification, Category, Purpose, Property, Group, GroupCategory

from .forms import SpecificationForm, GroupForm, CategoryForm

class SpecificationAdmin(admin.ModelAdmin):
    form = SpecificationForm
    list_display = ['name', 'internal_name', 'is_required',]

class GroupAdmin(admin.ModelAdmin):
    form = GroupForm
    list_display = ['name', 'internal_name']

class GroupCategoryInline(admin.TabularInline):
    model = GroupCategory

class CategoryAdmin(admin.ModelAdmin):
    form = CategoryForm
    list_display = ['name', 'singular_name', 'kind']
    inlines = [
        GroupCategoryInline,
    ]

class PurposeAdmin(admin.ModelAdmin):
    pass

class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'address', 'pub_date')

admin.site.register(Specification, SpecificationAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Purpose, PurposeAdmin)
admin.site.register(Property, PropertyAdmin)