from realty.models import PropertyImage, Property
from django.contrib.contenttypes.models import ContentType
from multimedia.models import Image
import os
from django.conf import settings

content_type = ContentType.objects.get_for_model(Property)
images = PropertyImage.objects.all()

for i in images:
	img = Image()
	img.img = i.img
	img.is_cover = i.is_cover
	img.object_id = i.property.id
	img.content_type = content_type
	img.save()

for i in Image.objects.all():	
	initial_path = i.img.path		
	i.img.name = i.img.name.split('properties/')[1]
	new_path = settings.MEDIA_ROOT + i.img.name
	# Move the file on the filesystem
	os.rename(initial_path, new_path)
	i.save()
