from copy import copy
from django import template
from django.urls import reverse_lazy, reverse
from django.utils.encoding import force_str
from django.template.loader import render_to_string
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe
from collections.abc import Iterable

import types
import re

from django.template import Context, TemplateDoesNotExist
from django.template.base import (
    FILTER_SEPARATOR,
    VariableNode,
    TextNode,
    Node,
    NodeList,
    TemplateSyntaxError,
    VariableDoesNotExist,
)

from django.core.exceptions import FieldDoesNotExist
from django.forms.utils import pretty_name


register = template.Library()


def silence_without_field(fn):
    """
    Args:
        fn:
    """

    def wrapped(field, attr):
        if not field:
            return ""
        return fn(field, attr)

    return wrapped


def _process_field_attributes(field, attr, process):

    # split attribute name and value from 'attr:value' string
    """
    Args:
        field:
        attr:
        process:
    """
    params = attr.split(":", 1)
    attribute = params[0]
    value = params[1] if len(params) == 2 else ""

    field = copy(field)

    # decorate field.as_widget method with updated attributes
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
    """
    Args:
        field:
        attr:
    """

    def process(widget, attrs, attribute, value):
        attrs[attribute] = value

    return _process_field_attributes(field, attr, process)


@register.filter("append_attr")
@silence_without_field
def append_attr(field, attr):
    """
    Args:
        field:
        attr:
    """

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
    """
    Args:
        field:
        css_class:
    """
    return append_attr(field, "class:" + css_class)


@register.filter(name="field_type")
def field_type(field):
    """Template filter that returns field class name (in lower case). E.g. if
    field is CharField then {{ field|field_type }} will return 'charfield'.

    Args:
        field:
    """
    if hasattr(field, "field") and field.field:
        return field.field.__class__.__name__.lower()
    return ""


@register.filter(name="widget_type")
def widget_type(field):
    """Template filter that returns field widget class name (in lower case).
    E.g. if field's widget is TextInput then {{ field|widget_type }} will return
    'textinput'.

    Args:
        field:
    """
    if (
        hasattr(field, "field")
        and hasattr(field.field, "widget")
        and field.field.widget
    ):
        return field.field.widget.__class__.__name__.lower()
    return ""


# ======================== render_field tag ==============================

ATTRIBUTE_RE = re.compile(
    r"""
    (?P<attr>
        [\w_-]+
    )
    (?P<sign>
        \+?=
    )
    (?P<value>
    ['"]? # start quote
        [^"']*
    ['"]? # end quote
    )
""",
    re.VERBOSE | re.UNICODE,
)

# ATTRIBUTE_RE = re.compile(r"""(?P<attr>[\w_-]+)(?P<sign>\+?=)(?P<value>['"]?[^"']*['"]?)""", re.VERBOSE | re.UNICODE)


@register.tag
def render_field(parser, token):
    """Render a form field using given attribute-value pairs

    Takes form field as first argument and list of attribute-value pairs for
    all other arguments. Attribute-value pairs should be in the form of
    attribute=value or attribute="a value" for assignment and attribute+=value
    or attribute+="value" for appending.

    Args:
        parser:
        token:
    """
    error_msg = (
        '%r tag requires a form field followed by a list of attributes and values in the form attr="value"'
        % token.split_contents()[0]
    )
    try:
        bits = token.split_contents()
        tag_name = bits[0]
        form_field = bits[1]
        attr_list = bits[2:]
    except ValueError:
        raise TemplateSyntaxError(error_msg)

    form_field = parser.compile_filter(form_field)

    attrs = []
    for pair in attr_list:
        match = ATTRIBUTE_RE.match(pair)
        if not match:
            raise TemplateSyntaxError(error_msg + ": %s" % pair)
        dct = match.groupdict()
        attr, value = dct["attr"], parser.compile_filter(dct["value"])

        attrs.append((attr, value))

    return FieldNode(form_field, attrs)


class FieldNode(Node):
    def __init__(self, field, attrs):
        """
        Args:
            field:
            attrs:
        """
        self.field = field
        self.attrs = attrs

    def render(self, context):
        """
        Args:
            context:
        """
        bounded_field = self.field.resolve(context)
        field = getattr(bounded_field, "field", None)

        with context.push():
            for key, value in self.attrs:
                if key == "class":
                    bounded_field = add_class(bounded_field, value.resolve(context))
                else:
                    context.update({key: value.resolve(context)})

            context.update({"field": bounded_field})
            widget = widget_type(bounded_field)

            template_name = "hydra/forms/{widget}.html".format(widget=widget)
            try:
                t = context.template.engine.get_template(template_name)
            except TemplateDoesNotExist:
                # Widgets sin plantilla propia (hidden, url, file...) se renderizan tal cual.
                return bounded_field
            return mark_safe(t.render(context))


@register.inclusion_tag("autosite/forms/form.html")
def render_form(form, **kwargs):
    """
    Args:
        form:
        **kwargs:
    """
    calculate_cols = len(form.fields) // 10
    if len(form.fields) % 10 > 0:
        calculate_cols += 1

    columns = int(kwargs["cols"]) if "cols" in kwargs else calculate_cols
    breakpoint = kwargs["breakpoint"] if "breakpoint" in kwargs else "md"
    col = 12 // columns
    col_class = "col-{breakpoint}-{col}".format(breakpoint=breakpoint, col=col)
    return {"form": form, "col": col_class}


# TEMPLATE TAGS PARA RECUPERAR VERBOSE_NAME
@register.filter
def verbose_name(obj):
    """
    Args:
        obj:
    """
    return obj._meta.verbose_name


@register.filter
def verbose_name_plural(obj):
    """
    Args:
        obj:
    """
    try:
        return obj._meta.verbose_name_plural
    except:
        pass


@register.simple_tag
def get_verbose_field_name(instance, field_name):
    """Returns verbose_name for a field.

    Args:
        instance:
        field_name:
    """
    return instance._meta.get_field(field_name).verbose_name.title()


@register.filter
def get_class(obj):
    """
    Args:
        obj:
    """
    return obj.model.__name__


# OBTENER LOS NOMBRES DE UN OBJETO
# GET MODEL INSTANCE FIELDS
# EJ. OBJECT.OBJECTS.GET(PK=1)
@register.filter
def get_field_names(obj):
    """
    Args:
        obj:
    """
    return obj._meta.fields
    # El siguiente metodo recupera incluso las tablas subrelacionadas
    # return obj._meta.get_fields()


@register.filter
def get_field_verbose_names(obj):
    """
    Args:
        obj:
    """
    return obj._meta.verbose_name.title()


from django.forms.models import model_to_dict


@register.simple_tag
def get_field_values(obj):
    """
    Args:
        obj:
    """
    return model_to_dict(obj)


# # LIST VIEW CON VALUES
# @register.simple_tag
# def obtener_cabeceras(instance, obj):
#     print(instance)
#     # instancia = instance.model.__name__
#     # objeto = eval(instancia)()
#     # for c in obj.keys():
#     #     a = objeto._meta.get_field(c).verbose_name.title()
#     #     print(a)
#     return True

# LIST VIEW CON VALUES
@register.simple_tag
def obtener_cabeceras(obj, numero):
    """
    Args:
        obj:
        numero:
    """
    objeto = model_to_dict(obj)
    cabeceras = []
    for c in objeto.keys():
        cabeceras.append(obj._meta.get_field(c).verbose_name.title())
    return cabeceras


@register.simple_tag
def obtener_valores(obj, numero):
    """
    Args:
        obj:
        numero:
    """
    objeto = model_to_dict(obj)
    objeto = model_to_dict(obj)
    valores = []
    for c in objeto.values():
        valores.append(c)
    return valores


@register.filter
def verbose_name_and_name(obj):
    """
    Args:
        obj:
    """
    objeto = model_to_dict(obj)
    lista = []
    for c in objeto.keys():
        lista.append(
            {"verbose_name": obj._meta.get_field(c).verbose_name.title(), "name": c}
        )
    return lista


from datetime import datetime, date

# VALIDAR SI ES FECHA
@register.filter
def is_date(val):
    """
    Args:
        val:
    """
    return isinstance(val, date)


@register.simple_tag
def get_headers(model_site):
    """
    Args:
        model_site:
    """
    headers = []
    for name in model_site.list_display:
        try:
            field = model_site.model._meta.get_field(name)
            label = field.verbose_name
        except FieldDoesNotExist:
            if name == "__str__":
                label = str(model_site.model._meta.verbose_name)
            else:
                if hasattr(model_site, name):
                    attr = getattr(model_site, name)
                elif hasattr(model_site.model, name):
                    attr = getattr(model_site.model, name)
                else:
                    raise AttributeError

                label = attr.__name__ if callable(attr) else attr
        finally:
            headers.append(pretty_name(label))

    return headers


@register.simple_tag
def get_results(model_site, queryset):
    """
    Args:
        model_site:
        queryset:
    """
    results = []
    for instance in queryset:
        try:
            slug_or_pk = instance.slug
        except:
            slug_or_pk = instance.id
        line = {
            "update_url": reverse_lazy(
                "site:%s_%s_editar" % model_site.get_info(), args=[instance.id]
            ),
            "detail_url": reverse_lazy(
                "site:%s_%s_detalle" % model_site.get_info(), args=[instance.id]
            ),
        }
        object_list = []
        for name in model_site.list_display:
            if name == "__str__":
                value = str(instance)
            else:
                if hasattr(model_site, name):
                    attr = getattr(model_site, name)
                elif hasattr(instance, name):
                    attr = getattr(instance, name)
                else:
                    raise AttributeError
                value = attr() if callable(attr) else attr
            object_list.append(value)
        line.update({"object_list": object_list})
        results.append(line)
    return results


@register.filter(name="zip")
def zip_lists(a, b):
    """
    Args:
        a:
        b:
    """
    return zip(a, b)


@register.simple_tag
def model_name(value):
    """
    Django template filter which returns the verbose name of a model.
    """
    if hasattr(value, "model"):
        value = value.model

    return value._meta.label.split(".")[-1]


@register.filter
def content_type(obj):
    if not obj:
        return False
    return ContentType.objects.get_for_model(obj).id


@register.filter
def has_permission(request, view_permissions):
    user = request.user
    if request.user.is_authenticated and request.user.is_superuser:
        return True
    permissions = list()
    if isinstance(view_permissions, Iterable):
        for model in view_permissions:
            permissions.append(f"{model._meta.app_label}.view_{model._meta.model_name}")
            permissions.append(f"{model._meta.app_label}.add_{model._meta.model_name}")
            permissions.append(
                f"{model._meta.app_label}.change_{model._meta.model_name}"
            )
    else:
        permissions.append(
            f"{view_permissions._meta.app_label}.view_{view_permissions._meta.model_name}"
        )
        permissions.append(
            f"{view_permissions._meta.app_label}.add_{view_permissions._meta.model_name}"
        )
        permissions.append(
            f"{view_permissions._meta.app_label}.change_{view_permissions._meta.model_name}"
        )
    return any(user.has_perm(permission) for permission in permissions)


@register.simple_tag
def permission(request, object, action):
    """Verificar si un usuario tiene un permiso de forma dinámica"""
    try:
        model = object.__class__
    except:
        model = object
    return request.user.has_perm(
        f"{model._meta.app_label}.{action}_{model._meta.model_name}"
    )


# def label_for_field(instance, name):
#     names = field.split('.')
#     name = names.pop(0)

#     if len(names) == 0:
#         if not name:
#             return None

#         attr = getattr(instance, name)

#         if callable(attr):
#             return  get_paragraph(attr(), 6)

#         return get_paragraph(str(attr), 6)

#     return get_attribute(getattr(instance, name), '.'.join(names))


@register.filter
def get_type(value):
    return type(value)
