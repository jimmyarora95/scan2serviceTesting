# website/templatetags/path_tags.py
from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def active(context, prefix: str):
    """
    Returns 'active' if current request.path starts with the given prefix.
    Usage: class="{% active '/portal/rooms/' %}"
    """
    path = context.get("request").path if context.get("request") else ""
    return "active" if isinstance(path, str) and path.startswith(prefix) else ""
