import base64
import os
import re

from django.conf import settings
from django.core.files.base import ContentFile

def base64_to_image(base64image):		
		format, imgstr = base64image.split(';base64,')		
		ext = format.split('/')[-1]

		data = ContentFile(base64.b64decode(imgstr))  
		
		return (data, ext)

def _read_icon_names(relative_path, prefix):
	"""Extrae los nombres de íconos (``.<prefix>-<nombre>:before``) de un CSS."""
	path = os.path.join(settings.BASE_DIR, relative_path)
	regex = re.compile(r'%s-(?P<icon>[\w_-]+):before' % prefix)
	try:
		with open(path, 'r', encoding='utf-8') as file:
			return sorted(set(regex.findall(file.read())))
	except OSError:
		return []


def get_category_icons():
	icons = _read_icon_names('static/plugins/fontcategories/fontcategories.css', 'fc')
	return [(icon, icon.capitalize()) for icon in icons]


def get_larbit_icons():
	icons = _read_icon_names('media/larbitfonts/style.css', 'lb')
	return [(icon, ' '.join(icon.capitalize().split('-'))) for icon in icons]
