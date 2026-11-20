from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Image


@admin.register(Image)
class ImageAdmin(ModelAdmin):
	pass
