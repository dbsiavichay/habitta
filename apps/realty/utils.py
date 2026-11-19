import os
import re

from django.conf import settings


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


def get_spec_icons():
	"""Íconos de especificaciones (clases ``lb-*``) de la fuente subida desde el admin."""
	icons = _read_icon_names('media/larbitfonts/style.css', 'lb')
	return [(icon, ' '.join(icon.capitalize().split('-'))) for icon in icons]


# Alias histórico: lo referencia la migración realty/0006 y no debe romperse.
get_larbit_icons = get_spec_icons
