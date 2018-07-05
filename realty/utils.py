import re
import base64
from django.core.files.base import ContentFile

def base64_to_image(base64image):		
		format, imgstr = base64image.split(';base64,')		
		ext = format.split('/')[-1]

		data = ContentFile(base64.b64decode(imgstr))  
		
		return (data, ext)

def get_fontawesome_icons():
	file = open('static/plugins/fontawesome/fontawesome.min.css', 'r')
	regex = regex = re.compile(r'fa-(?P<icon>[\w_-]+):before')
	for line in file:
	    match = regex.findall(line)    	    
	    icons = [icon for icon in match]
	
	icons = sorted(icons)	    

	return [(icon, icon) for icon in icons]