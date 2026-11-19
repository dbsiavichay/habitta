from django import template
from django.template.loader import render_to_string

from ..forms import LogForm
from ..models import Log

register = template.Library()


def like_context(obj, user):
    """Estado del botón "Me gusta" (favorito) de una publicación para un usuario."""
    context = {
        'property': obj,
        'likes': Log.objects.filter(type=Log.LIKE, property=obj).count(),
        'log': None,
        'log_form': None,
    }
    if getattr(user, 'is_authenticated', False):
        log = Log.objects.filter(type=Log.LIKE, property=obj, user=user).first()
        if log:
            context['log'] = log
        else:
            context['log_form'] = LogForm(initial={'type': Log.LIKE, 'property': obj})
    return context


def render_like(obj, user, request=None):
    return render_to_string('logs/like.html', like_context(obj, user), request=request)


class LikeNode(template.Node):
    def __init__(self, obj, user):
        self.obj = template.Variable(obj)
        self.user = template.Variable(user)

    def render(self, context):
        obj = self.obj.resolve(context)
        user = self.user.resolve(context)
        return render_like(obj, user, context.get('request'))


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
