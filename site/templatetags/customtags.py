from decimal import Decimal

from django import template

from billy.web.public.views import templatename
from billy.web.public.forms import StateSelectForm


register = template.Library()


@register.inclusion_tag(templatename('state_select_form'))
def state_select_form():
    return {'form':  StateSelectForm}


@register.inclusion_tag(templatename('sources'))
def sources(obj):
    return {'sources': obj['sources']}


@register.filter
def plusfield(object, key):
    return object['+' + key]


@register.filter
def decimal_format(value, TWOPLACES=Decimal(100) ** -2):
    'Format a decimal.Decimal like to 2 decimal places.'
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(TWOPLACES)
