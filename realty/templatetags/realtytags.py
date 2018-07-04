from django import template
from realty.models import Specification

register = template.Library()

@register.filter(name='icon')
def get_specification_icon(pk): 
	try:
		specification = Specification.objects.get(pk=pk)
		return specification.icon
	except Specification.DoesNotExist:
		raise ValueError('No existe el objeto %s' % pk)
    