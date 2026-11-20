"""Renderizado de campos de formulario con las plantillas de ``templates/hydra/forms/``.

- ``{% render_field field attr="valor" class="extra" %}``: pinta el campo con la plantilla de su
  widget (``hydra/forms/<widget>.html``). ``class`` se suma a las clases del widget; el resto de
  atributos pasa al contexto de la plantilla (p. ej. ``icon="mail"``).
- ``{{ field|add_class:"input w-full" }}`` y ``{{ field|attr:"aria-invalid:true" }}``.

Basado en django-widget-tweaks. ``attr`` parte en el primer ``:``, así que no sirve para atributos
de Alpine (``:type``, ``x-bind:``).
"""
import re
import types
from copy import copy

from django import template
from django.template import TemplateDoesNotExist
from django.template.base import Node, TemplateSyntaxError
from django.utils.safestring import mark_safe

register = template.Library()


def silence_without_field(fn):
    def wrapped(field, attr):
        if not field:
            return ""
        return fn(field, attr)

    return wrapped


def _process_field_attributes(field, attr, process):
    # 'atributo:valor' → ('atributo', 'valor')
    params = attr.split(":", 1)
    attribute = params[0]
    value = params[1] if len(params) == 2 else ""

    field = copy(field)

    # Envuelve field.as_widget para aplicar los atributos al renderizar
    old_as_widget = field.as_widget

    def as_widget(self, widget=None, attrs=None, only_initial=False):
        attrs = attrs or {}
        process(widget or self.field.widget, attrs, attribute, value)
        html = old_as_widget(widget, attrs, only_initial)
        self.as_widget = old_as_widget
        return html

    field.as_widget = types.MethodType(as_widget, field)
    return field


@register.filter("attr")
@silence_without_field
def set_attr(field, attr):
    def process(widget, attrs, attribute, value):
        attrs[attribute] = value

    return _process_field_attributes(field, attr, process)


@register.filter("append_attr")
@silence_without_field
def append_attr(field, attr):
    def process(widget, attrs, attribute, value):
        if attrs.get(attribute):
            attrs[attribute] += " " + value
        elif widget.attrs.get(attribute):
            attrs[attribute] = widget.attrs[attribute] + " " + value
        else:
            attrs[attribute] = value

    return _process_field_attributes(field, attr, process)


@register.filter("add_class")
@silence_without_field
def add_class(field, css_class):
    return append_attr(field, "class:" + css_class)


@register.filter(name="widget_type")
def widget_type(field):
    """Nombre de la clase del widget en minúsculas: TextInput → 'textinput'."""
    if hasattr(field, "field") and hasattr(field.field, "widget") and field.field.widget:
        return field.field.widget.__class__.__name__.lower()
    return ""


# ======================== render_field ==============================

ATTRIBUTE_RE = re.compile(
    r"""
    (?P<attr>
        [\w_-]+
    )
    (?P<sign>
        \+?=
    )
    (?P<value>
    ['"]? # comilla inicial
        [^"']*
    ['"]? # comilla final
    )
""",
    re.VERBOSE | re.UNICODE,
)


@register.tag
def render_field(parser, token):
    """``{% render_field form.campo attr="valor" ... %}``"""
    error_msg = (
        '%r tag requires a form field followed by a list of attributes and values in the form attr="value"'
        % token.split_contents()[0]
    )
    try:
        bits = token.split_contents()
        form_field = bits[1]
        attr_list = bits[2:]
    except (ValueError, IndexError):
        raise TemplateSyntaxError(error_msg)

    form_field = parser.compile_filter(form_field)

    attrs = []
    for pair in attr_list:
        match = ATTRIBUTE_RE.match(pair)
        if not match:
            raise TemplateSyntaxError(error_msg + ": %s" % pair)
        dct = match.groupdict()
        attrs.append((dct["attr"], parser.compile_filter(dct["value"])))

    return FieldNode(form_field, attrs)


class FieldNode(Node):
    def __init__(self, field, attrs):
        self.field = field
        self.attrs = attrs

    def render(self, context):
        bounded_field = self.field.resolve(context)

        with context.push():
            for key, value in self.attrs:
                if key == "class":
                    bounded_field = add_class(bounded_field, value.resolve(context))
                else:
                    context.update({key: value.resolve(context)})

            context.update({"field": bounded_field})
            template_name = "hydra/forms/{widget}.html".format(widget=widget_type(bounded_field))
            try:
                t = context.template.engine.get_template(template_name)
            except TemplateDoesNotExist:
                # Widgets sin plantilla propia (p. ej. HiddenInput) se renderizan tal cual.
                return bounded_field
            return mark_safe(t.render(context))
