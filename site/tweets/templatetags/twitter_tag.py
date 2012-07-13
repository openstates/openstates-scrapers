from django import template
from ..latest_tweet import get_latest_tweet

register = template.Library()

@register.simple_tag
def latest_tweet():
    tweet = get_latest_tweet()
    if tweet:
        return tweet['text']
    else:
        return ''
