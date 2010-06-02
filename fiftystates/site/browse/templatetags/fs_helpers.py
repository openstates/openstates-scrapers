from fiftystates.backend import db, metadata

from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
@stringfilter
def state_name(abbrev):
    return metadata(abbrev)['state_name']


@register.filter
def chamber(role):
    if role['type'] == 'member':
        return metadata(role['state'])['%s_chamber_name' % role['chamber']]
    return ''


@register.filter
def short_chamber(role):
    long = chamber(role)
    if long == 'House of Representatives':
        return 'House'
    return long


@register.filter
def title(role):
    if role['type'] == 'member':
        return metadata(role['state'])['%s_title' % role['chamber']]
    return ''
