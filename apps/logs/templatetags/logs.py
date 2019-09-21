from django import template
from django.template.loader import render_to_string
from ..models import Log
from ..forms import LogForm

register = template.Library()

class LikeNode(template.Node):
    def __init__(self, obj, user):    	
        self.obj = template.Variable(obj)
        self.user = template.Variable(user)

    def render(self, context):
        obj = self.obj.resolve(context)        
        user = self.user.resolve(context)

        if not user.is_authenticated:
        	return ''

        context_dict = context.flatten()        
        try:
        	log = Log.objects.get(type=Log.LIKE, property=obj, user=user)
        	context_dict['log'] = log
        except Log.DoesNotExist:
        	form = LogForm(initial={'type':Log.LIKE, 'property': obj})
        	context_dict['log_form'] = form
        	
        liststr = render_to_string(['logs/like.html'], context_dict)
        return liststr              

@register.tag(name='like_log')
def like_log(parser, token):
	"""
	Syntax:
		{% like_log [object] [user] %}
	"""
	try:
  		tag_name, obj, user = token.split_contents()
	except ValueError:
		raise template.TemplateSyntaxError("%r tag requires 2 arguments" % token.contents.split()[0])

	return LikeNode(obj, user)