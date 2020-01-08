import tinify
import os
from django.conf import settings

from apps.realty.models import Property


tinify.key = settings.TINIFY_API_KEY

properties = Property.objects.all()

for p in properties:
	cover = p.get_cover_instance()
	if cover:
		path = cover.img.path
		source = tinify.from_file(path)
		print('Input Image Size  : ', os.path.getsize(path))
		source.to_file(path)
		print('Output Image Size  : ', os.path.getsize(path))
		print('=======*******=========')