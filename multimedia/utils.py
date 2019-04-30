import re
import base64
from django.core.files.base import ContentFile

def base64_to_image(base64image):		
		format, imgstr = base64image.split(';base64,')		
		ext = format.split('/')[-1]

		data = ContentFile(base64.b64decode(imgstr))  
		
		return (data, ext)