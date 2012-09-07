'''This is the action categorization code I added to Tennessee,
factored out into functions that might be reusable.
'''
import re
from collections import namedtuple


class Rule(namedtuple('Rule', 'regex types stop attrs')):
    '''If ``regex`` matches the action text, the resulting action's
    types should include ``types``.

    If stop is true, no other rules should be tested after this one;
    in other words, this rule conclusively determines the action's
    types and attrs.

    The resulting action should contain ``attrs``, which basically
    enables overwriting certain attributes, like the chamber if
    the action was listed in the wrong column.
    '''
    def __new__(_cls, regex, types=None, stop=True, **kwargs):
        'Create new instance of Rule(regex, types, attrs, stop)'

        # Types can be a string or a sequence.
        if isinstance(types, basestring):
            types = set([types])
        types = set(types or [])

        # If no types are associated, assume that the categorizer
        # should continue looking at other rules.
        if not types:
            stop = False
        return tuple.__new__(_cls, (regex, types, stop, kwargs))


def categorize_action(action, rules=[]):
    types = set()
    attrs = {}

    for rule in rules:

        # Try to match the regex.
        m = re.search(rule.regex, action)
        if m or (rule.regex in action):
            # If so, apply its associated types to this action.
            types |= rule.types

            # Also add its specified attrs.
            attrs.update(m.groupdict())
            attrs.update(rule.attrs)

            # Break if the rule says so, otherwise continue testing against
            # other rules.
            if rule.stop is True:
                break

    # Returns types, attrs
    return list(types), attrs
