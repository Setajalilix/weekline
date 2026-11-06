from django import template

from performance.services.reporting import format_minutes

register = template.Library()


@register.filter
def duration(minutes):
    try:
        return format_minutes(int(minutes or 0))
    except (TypeError, ValueError):
        return "0m"


@register.filter
def as_iso(value):
    if not value:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    return str(value)[:10]


@register.filter
def as_hm(value):
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%H:%M")
    return str(value)[:5]


@register.filter
def pct(value):
    try:
        return f"{float(value):.0f}%"
    except (TypeError, ValueError):
        return "0%"
