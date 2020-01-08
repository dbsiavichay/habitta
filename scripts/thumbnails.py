import os
from PIL import Image
from apps.realty.models import Property

properties = Property.objects.all()

size = 320, 180
for p in properties:
	cover = p.get_cover_instance()
	if cover:
		path = cover.img.path
		im = Image.open(path)
		im.thumbnail(size)
		p.add_image(im, 'thumbnail')