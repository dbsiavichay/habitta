from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .forms import CategoryForm, GroupForm, SpecificationForm
from .models import Category, Group, GroupCategory, Property, Purpose, Specification


@admin.register(Specification)
class SpecificationAdmin(ModelAdmin):
    form = SpecificationForm
    list_display = ['name', 'internal_name', 'is_required']


@admin.register(Group)
class GroupAdmin(ModelAdmin):
    form = GroupForm
    list_display = ['name', 'internal_name']


class GroupCategoryInline(TabularInline):
    model = GroupCategory


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    form = CategoryForm
    list_display = ['name', 'singular_name', 'kind']
    inlines = [
        GroupCategoryInline,
    ]


@admin.register(Purpose)
class PurposeAdmin(ModelAdmin):
    pass


@admin.register(Property)
class PropertyAdmin(ModelAdmin):
    list_display = ('title', 'description', 'address', 'pub_date')
