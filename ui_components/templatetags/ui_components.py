from copy import copy
from django import template
from django.urls import reverse_lazy
from django.utils.encoding import force_text
from django.template.loader import render_to_string

from django.utils.safestring import mark_safe
import types
import re

from django.template import Context
from django.template.base import (     
    FILTER_SEPARATOR, VariableNode, TextNode,
    Node, NodeList, TemplateSyntaxError, VariableDoesNotExist,    
)

register = template.Library()

class TableNode(Node):
    child_nodelists = ('nodelist_headers', 'nodelist_loop',)

    def __init__(self, loopvars, sequence, is_edit, nodelist_headers, nodelist_loop):        
        self.loopvars, self.sequence = loopvars, sequence
        self.is_edit = is_edit
        self.nodelist_headers, self.nodelist_loop = nodelist_headers, nodelist_loop        

    def __repr__(self):
        edit_text = ' edit' if self.is_edit else ''
        return "<Table Node: ui_table %s in %s, tail_len: %d%s>" % \
            (', '.join(self.loopvars), self.sequence, len(self.nodelist_loop),
             edit_text)

    def __iter__(self):        
        for node in self.nodelist_loop:
            yield node        

    def render(self, context):        
        self.nodelist_headers = [node for node in self.nodelist_headers if not isinstance(node, TextNode)]
        self.nodelist_loop = [node for node in self.nodelist_loop if not isinstance(node, TextNode)]

        len_nodelist_headers = len(self.nodelist_headers)
        len_nodelist_loop = len(self.nodelist_loop)

        if len_nodelist_headers != len_nodelist_loop:
            raise ValueError(
                "There are {} headers and {} column values, need the same length"
                .format(len_nodelist_headers, len_nodelist_loop),
            )

        if 'forloop' in context:
            parentloop = context['forloop']
        else:
            parentloop = {}
        with context.push():
            try:
                values = self.sequence.resolve(context, True)
            except VariableDoesNotExist:
                values = []
            if values is None:
                values = []
            if not hasattr(values, '__len__'):
                values = list(values)
            len_values = len(values)

            num_loopvars = len(self.loopvars)
            unpack = num_loopvars > 1
            # Create a forloop value in the context.  We'll update counters on each
            # iteration just below.
            loop_dict = context['forloop'] = {'parentloop': parentloop}            

            rows = []
            for i, item in enumerate(values):
                # Shortcuts for current loop iteration number.                
                loop_dict['counter'] = i + 1
                              
                # Boolean values designating first and last times through loop.
                loop_dict['first'] = (i == 0)
                loop_dict['last'] = (i == len_values - 1)

                pop_context = False
                if unpack:
                    # If there are multiple loop variables, unpack the item into
                    # them.
                    try:
                        len_item = len(item)
                    except TypeError:  # not an iterable
                        len_item = 1
                    # Check loop variable count before unpacking
                    if num_loopvars != len_item:
                        raise ValueError(
                            "Need {} values to unpack in for loop; got {}. "
                            .format(num_loopvars, len_item),
                        )
                    unpacked_vars = dict(zip(self.loopvars, item))
                    pop_context = True
                    context.update(unpacked_vars)
                else:                    
                    context[self.loopvars[0]] = item                                

                row = []
                for node in self.nodelist_loop:                    
                    result = node.render_annotated(context)                    
                    t = context.template.engine.get_template('ui_components/table/td.html')
                    td = t.render(Context({'td': result}, autoescape=context.autoescape))                                        
                    row.append(td)

                t = context.template.engine.get_template('ui_components/table/tr.html')
                tr = t.render(Context({'row': row, 'is_edit': self.is_edit, 'object': item}, autoescape=context.autoescape))
                rows.append(tr)

                if pop_context:
                    # The loop variables were pushed on to the context so pop them
                    # off again. This is necessary because the tag lets the length
                    # of loopvars differ to the length of each set of items and we
                    # don't want to leave any vars from the previous loop on the
                    # context.
                    context.pop()
            
            headers = []
            for node in self.nodelist_headers:
                header = node.render_annotated(context)
                headers.append(header) 

            if self.is_edit:
                headers.append('Editar')

            t = context.template.engine.get_template('ui_components/table/table.html')
            table = t.render(Context({ 'headers':headers, 'rows': rows}, autoescape=context.autoescape))            
        
        return mark_safe(table)

@register.tag('ui_table')
def ui_table(parser, token):
    bits = token.split_contents()
    if len(bits) < 4:
        raise TemplateSyntaxError("'ui_table' statements should have at least four"
                                  " words: %s" % token.contents)

    is_edit = bits[-1] == 'edit'
    in_index = -3 if is_edit else -2
    if bits[in_index] != 'in':
        raise TemplateSyntaxError("'ui_table' statements should use the format"
                                  " 'ui_table x in y': %s" % token.contents)

    invalid_chars = frozenset((' ', '"', "'", FILTER_SEPARATOR))
    loopvars = re.split(r' *, *', ' '.join(bits[1:in_index]))    
    for var in loopvars:
        if not var or not invalid_chars.isdisjoint(var):
            raise TemplateSyntaxError("'ui_table' tag received an invalid argument:"
                                      " %s" % token.contents)

    sequence = parser.compile_filter(bits[in_index + 1])
    nodelist_headers = parser.parse(('body', 'endui_table'))        
    token = parser.next_token()
    if token.contents == 'body':
        nodelist_loop = parser.parse(('endui_table',))        
        parser.delete_first_token()
    else:
        nodelist_empty = None    

    return TableNode(loopvars, sequence, is_edit, nodelist_headers, nodelist_loop)

#####FORMS######
@register.inclusion_tag('ui_components/form.html')
def ui_form(form):    
    return {
        'form':form,        
    }

#####INPUTS######
@register.inclusion_tag('ui_components/inputs/input.html')
def ui_input(field, icon=None):    
    return {
        'field':field,
        'icon':icon,        
    }

@register.inclusion_tag('ui_components/inputs/select.html')
def ui_select(field):
    return {
        'field':field,        
    }

@register.inclusion_tag('ui_components/inputs/datetimepicker.html')
def ui_datepicker(field):    
    return {
        'field':field,        
    }

###BUTTONS####
@register.inclusion_tag('ui_components/button.html')
def ui_button(obj, icon, color, size=None, name = None):
    if name is not None:
        url = reverse_lazy(name, args=[obj])
    else:
        url = obj.get_absolute_url()
    return {
        'url':url,
        'icon':icon,
        'color':color,
        'size':size,
    }


###FILTERS####
@register.filter(name='ui_input_type')
def hash(input):     
    return input.field.widget.__class__.__name__

@register.filter(name='hash')
def hash(h, key):     
    return h[key]

@register.filter(name='ui_row_cells')
def quit_tr(row):        
    return mark_safe(row.replace('<tr>','').replace('</tr>',''))






























def silence_without_field(fn):
    def wrapped(field, attr):
        if not field:
            return ""
        return fn(field, attr)
    return wrapped


def _process_field_attributes(field, attr, process):

    # split attribute name and value from 'attr:value' string
    params = attr.split(':', 1)
    attribute = params[0]
    value = params[1] if len(params) == 2 else ''

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

    def process(widget, attrs, attribute, value):
        attrs[attribute] = value

    return _process_field_attributes(field, attr, process)


@register.filter("append_attr")
@silence_without_field
def append_attr(field, attr):
    def process(widget, attrs, attribute, value):
        if attrs.get(attribute):
            attrs[attribute] += ' ' + value
        elif widget.attrs.get(attribute):
            attrs[attribute] = widget.attrs[attribute] + ' ' + value
        else:
            attrs[attribute] = value
    return _process_field_attributes(field, attr, process)


@register.filter("add_class")
@silence_without_field
def add_class(field, css_class):
    return append_attr(field, 'class:' + css_class)


@register.filter(name='field_type')
def field_type(field):
    """
    Template filter that returns field class name (in lower case).
    E.g. if field is CharField then {{ field|field_type }} will
    return 'charfield'.
    """
    if hasattr(field, 'field') and field.field:
        return field.field.__class__.__name__.lower()
    return ''


@register.filter(name='widget_type')
def widget_type(field):
    """
    Template filter that returns field widget class name (in lower case).
    E.g. if field's widget is TextInput then {{ field|widget_type }} will
    return 'textinput'.
    """
    if hasattr(field, 'field') and hasattr(field.field, 'widget') and field.field.widget:
        return field.field.widget.__class__.__name__.lower()
    return ''


# ======================== render_field tag ==============================

ATTRIBUTE_RE = re.compile(r"""
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
""", re.VERBOSE | re.UNICODE)

#ATTRIBUTE_RE = re.compile(r"""(?P<attr>[\w_-]+)(?P<sign>\+?=)(?P<value>['"]?[^"']*['"]?)""", re.VERBOSE | re.UNICODE)

@register.tag
def render_field(parser, token):
    """
    Render a form field using given attribute-value pairs

    Takes form field as first argument and list of attribute-value pairs for
    all other arguments.  Attribute-value pairs should be in the form of
    attribute=value or attribute="a value" for assignment and attribute+=value
    or attribute+="value" for appending.
    """
    error_msg = '%r tag requires a form field followed by a list of attributes and values in the form attr="value"' % token.split_contents()[0]
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
        attr, value = dct['attr'], parser.compile_filter(dct['value'])
        
        attrs.append((attr, value))
        

    return FieldAttributeNode(form_field, attrs)


class FieldAttributeNode(Node):
    def __init__(self, field, attrs):
        self.field = field
        self.attrs = attrs

    def render(self, context):
        bounded_field = self.field.resolve(context)
        field = getattr(bounded_field, 'field', None)        

        template_name = None
        with context.push():
            for key, value in self.attrs:
                if key == 'class':                    
                    bounded_field = set_attr(bounded_field, 'class:%s' % value.resolve(context))                
                else:
                    context.update({key:value.resolve(context)})

            context.update({'field': bounded_field})
            
            if widget_type(bounded_field) == 'select':
                template_name = 'ui_components/inputs/select.html'
            elif widget_type(bounded_field) == 'checkboxselectmultiple':
                template_name = 'ui_components/inputs/checkboxselectmultiple.html'
            else:
                template_name = 'ui_components/inputs/input.html'

            t = context.template.engine.get_template(template_name)
            component = t.render(context)

            context.pop()
        
        return mark_safe(component)


@register.tag
def render_component(parser, token):
    """
    Render a form field using given attribute-value pairs

    Takes form field as first argument and list of attribute-value pairs for
    all other arguments.  Attribute-value pairs should be in the form of
    attribute=value or attribute="a value" for assignment and attribute+=value
    or attribute+="value" for appending.
    """
    error_msg = '%r tag requires a form field followed by a list of attributes and values in the form attr="value"' % token.split_contents()[0]
    try:
        bits = token.split_contents()
        tag_name = bits[0]        
        attr_list = bits[1:]
    except ValueError:
        raise TemplateSyntaxError(error_msg)

    attrs = []
    for pair in attr_list:
        match = ATTRIBUTE_RE.match(pair)
        if not match:
            raise TemplateSyntaxError(error_msg + ": %s" % pair)
        dct = match.groupdict()
        attr, value = dct['attr'], parser.compile_filter(dct['value'])
        
        attrs.append((attr, value))
        
    return ComponentNode(attrs)


class ComponentNode(Node):
    def __init__(self, attrs):        
        self.attrs = attrs

    def render(self, context):        
        template = None
        with context.push():
            for key, value in self.attrs:                
                if key == 'template':
                    template = value.resolve(context)
                else:
                    context.update({key:value.resolve(context)})

            t = context.template.engine.get_template(template)
            component = t.render(context)

            context.pop()
        
        return mark_safe(component)
