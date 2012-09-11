import re
from functools import partial
from collections import namedtuple


class Rule(namedtuple('Rule', 'regexes types stop attrs')):
    '''If anyh of ``regexes`` matches the action text, the resulting
    action's types should include ``types``.

    If stop is true, no other rules should be tested after this one;
    in other words, this rule conclusively determines the action's
    types and attrs.

    The resulting action should contain ``attrs``, which basically
    enables overwriting certain attributes, like the chamber if
    the action was listed in the wrong column.
    '''
    def __new__(_cls, regexes, types=None, stop=False, **kwargs):
        'Create new instance of Rule(regex, types, attrs, stop)'

        # Regexes can be a string or a sequence.
        if isinstance(regexes, basestring):
            regexes = set([regexes])
        regexes = set(regexes or [])

        # Types can be a string or a sequence.
        if isinstance(types, basestring):
            types = set([types])
        types = set(types or [])

        return tuple.__new__(_cls, (regexes, types, stop, kwargs))


class BaseCategorizer(object):
    '''A class that exposes a main categorizer function
    and before and after hooks, in case a state requires specific
    steps that make use of action or category info. The return
    value is a 2-tuple of category types and a dictionary of
    attributes to overwrite on the target action object.
    '''
    rules = []

    def categorize(self, text):

        whitespace = partial(re.sub, '\s{1,4}', '\s{,4}')

        # Run the before hook.
        text = self.before_categorize(text)

        types = set()
        attrs = {}
        for rule in self.rules:

            for regex in rule.regexes:

                # Try to match the regex.
                m = re.search(whitespace(regex), text)
                if m or (regex in text):
                    # If so, apply its associated types to this action.
                    types |= rule.types

                    # Also add its specified attrs.
                    attrs.update(m.groupdict())
                    attrs.update(rule.attrs)

                    # Break if the rule says so, otherwise
                    # continue testing against other rules.
                    if rule.stop is True:
                        break

        # Returns types, attrs
        return_val = (list(types), attrs)
        return self.after_categorize(return_val)

    def before_categorize(self, text):
        return text

    def after_categorize(self, return_val):
        return return_val


# These are regex patterns that map to action categories.
_categorizer_rules = (

    # Parse vote counts--possibly useful in future.
    Rule('Roll\s+Call\s+\d+:\s+yeas\s+(?P<yes_votes>\d+),'
         '\s+nays\s+(?P<no_votes>\d+)'),
    Rule(r'(?i)voice vote', voice_vote=True),
    Rule(r'Effective (?P<effective_date>.+)'),

    # Same for member names.
    Rule(('(?i)(co)?authored by (representative|senator)s?\s+'
          '(?P<legislators>.+)')),
    Rule((r'(?P<version>Amendment \d+)\s+\(\s*(?P<legislators>.+?)\)'
          r'.+?failed'), 'amendment:failed'),
    Rule((r'(?P<version>Amendment \d+)\s+\(\s*(?P<legislators>.+?)\)'
          r'.+?withdrawn'), 'amendment:withdrawn'),
    Rule((r'(?P<version>Amendment \d+)\s+\(\s*(?P<legislators>.+?)\)'
          r'.+ruled out of order'), 'amendment:failed'),
    Rule(r'(?i)^(senator|representative)s?(?P<legislators>.+?)\s+added'),
    Rule(r'(?i)^Senate\s+(advisor|sponsor|conferee)s?.*?:\s+'
         r'(?P<legislators>.+)'),

    # Amendments.
    Rule((r'(?P<version>Amendment \d+)\s+\(\s*(?P<legislators>.+?)\)'
          r'.+?prevailed'), 'amendment:passed'),
    Rule(r'(?i)(house|senate) concurred in (house|senate) amendments',
         'amendment:passed'),

    # Readings.
    Rule(r'(?i)^first reading:', ('bill:introduced', 'bill:reading:1')),
    Rule(r'(?i)^second reading:', 'bill:reading:2'),
    Rule(r'(?i)^third reading:', 'bill:reading:3'),

    # Committees.
    Rule(r'Committee report:.+?do pass', 'committee:passed:favorable'),
    Rule([r'(?i)referred to (?P<committee>.+)',
          r'(?i)reassigned to (?P<committee>.+)'], 'committee:referred'),
    Rule(r'(?i)Committee report:.*?do pass', 'committee:passed:favorable'),
    Rule(r'(?i)motion to recommit to (?P<committee>.+?)'
         r'\((?P<legislators>.+?)\)'),

    # Passage/failure.
    Rule(r'passed', 'bill:passed'),
    Rule(r'Third reading: passed', 'bill:passed'),

    # Weird.
    Rule(r'Conference committee.+adopted',
         ['committee:passed', 'amendment:passed']),

    # Governor.
    Rule(r'Signed by the Governor', 'governor:signed'),
    )


class Categorizer(BaseCategorizer):
    rules = _categorizer_rules
