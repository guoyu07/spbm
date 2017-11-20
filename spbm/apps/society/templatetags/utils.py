from django import template
from django_jinja import library
import jinja2


@library.global_function
@jinja2.contextfilter
def active(context, *tokens):
    """
    Allows you to specify tokens to receive 'active' attribute for.

    :param context:
    :param token: List of tokens to accept.
    :return: active if within, or none if not.
    """
    if len(tokens) < 1:
        raise template.TemplateSyntaxError("%r tag requires at least one argument" % template_tag)

    path = context['request'].path
    for p in tokens:
        path_value = template.Variable(p).resolve(context)
        if path == path_value:
            # Change to customize to correct class you wish to have
            return "active"
    return ""
