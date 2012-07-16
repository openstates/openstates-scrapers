import os
import random

from django import template


register = template.Library()

@register.simple_tag
def funfact(abbr, data={}):
    try:
        here = os.path.abspath(os.path.dirname(__file__))
        with open(os.path.join(here, '..', abbr + '.txt')) as f:
            facts = f.read()
    except IOError:
        return ''
    facts = filter(None, facts.splitlines())
    return random.choice(facts)

