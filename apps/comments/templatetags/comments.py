from django import template
from django.template.loader import render_to_string
from django.contrib.contenttypes.models import ContentType
from ..models import Comment
from ..forms import CommentForm

register = template.Library()

class CommentListNode(template.Node):
    def __init__(self, obj, template_name):    	
        self.obj = template.Variable(obj)
        self.template_name = template_name

    def render(self, context):
        obj = self.obj.resolve(context)        
        ctype = ContentType.objects.get_for_model(obj)
        comments = Comment.objects.filter(contenttype = ctype, object_id=obj.id)

        context_dict = context.flatten()        
        context_dict['comments'] = comments
        liststr = render_to_string([self.template_name], context_dict)
        return liststr        

class CommentFormNode(template.Node):
    def __init__(self, obj, template_name):    	
        self.obj = template.Variable(obj)
        self.template_name = template_name

    def render(self, context):
        obj = self.obj.resolve(context)
        ctype = ContentType.objects.get_for_model(obj)        
        form = CommentForm(initial={'contenttype':ctype, 'object_id':obj.id})

        context_dict = context.flatten()        
        context_dict['form'] = form
        formstr = render_to_string([self.template_name], context_dict)
        return formstr        

@register.tag(name='comment_list')
def comment_list(parser, token):
	"""
	Syntax:
		{% comment_list [object] template %}
	"""
	try:
		tag_name, obj, template_name = token.split_contents()		
	except ValueError:
		raise template.TemplateSyntaxError("%r tag requires a single argument" % token.contents.split()[0])

	return CommentListNode(obj, template_name[1:-1])

@register.tag(name='comment_form')
def comment_form(parser, token):
	"""
	Syntax:
		{% comment_form [object] template %}
	"""
	try:
  		tag_name, obj, template_name = token.split_contents()
	except ValueError:
		raise template.TemplateSyntaxError("%r tag requires a single argument" % token.contents.split()[0])

	return CommentFormNode(obj, template_name[1:-1])

@register.simple_tag
def comments_count(obj):
    ctype = ContentType.objects.get_for_model(obj)
    comments = Comment.objects.filter(contenttype=ctype, object_id=obj.id)
    return comments.count()