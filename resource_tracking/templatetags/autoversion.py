from django import template
from resource_tracking.templatetags import get_resource_file

register = template.Library()
@register.filter(name="autoversion")
def autoversion(resource_file):
    return get_resource_file(resource_file)
