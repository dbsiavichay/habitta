import re
import base64
from django.core.files.base import ContentFile

def base64_to_image(base64image):		
		format, imgstr = base64image.split(';base64,')		
		ext = format.split('/')[-1]

		data = ContentFile(base64.b64decode(imgstr))  
		
		return (data, ext)

def get_category_icons():
	CHOICES = []
	file = open('static/plugins/fontcategories/fontcategories.css', 'r')
	regex = regex = re.compile(r'fc-(?P<icon>[\w_-]+):before')
	for line in file:
	    match = regex.findall(line)    	    	    
	    CHOICES = CHOICES + [icon for icon in match]
	
	CHOICES = sorted(CHOICES)
	CHOICES = [(icon, icon.capitalize()) for icon in CHOICES]
	return CHOICES

def get_larbit_icons():
	return []
	CHOICES = []
	file = open('media/larbitfonts/style.css', 'r')
	regex = regex = re.compile(r'lb-(?P<icon>[\w_-]+):before')
	for line in file:
	    match = regex.findall(line)    	    	    
	    CHOICES = CHOICES + [icon for icon in match]
	
	CHOICES = sorted(CHOICES)
	CHOICES = [(icon, ' '.join(icon.capitalize().split('-'))) for icon in CHOICES]
	return CHOICES