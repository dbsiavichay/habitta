import re


def get_fontawesome_icons():
	file = open('static/plugins/fontawesome/fontawesome.min.css', 'r')
	regex = regex = re.compile(r'fa-(?P<icon>[\w_-]+):before')
	for line in file:
	    match = regex.findall(line)    	    
	    icons = [icon for icon in match]
	
	icons = sorted(icons)	    

	return [(icon, icon) for icon in icons]