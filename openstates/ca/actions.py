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

        # Types can be a string or a sequence.
        if isinstance(regexes, basestring):
            regexes = set([regexes])
        regexes = set(regexes or [])

        # Types can be a string or a sequence.
        if isinstance(types, basestring):
            types = set([types])
        types = set(types or [])

        # If no types are associated, assume that the categorizer
        # should continue looking at other rules.
        if not types:
            stop = False
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
        for rule in _categorizer_rules:

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

    Rule((r'\(Ayes (?P<yes_votes>\d+)\.\s+Noes\s+'
          r'(?P<no_votes>\d+)\.( Page \S+\.)?\)')),

    Rule(r'^Introduced', 'bill:introduced'),

    Rule(r'(?i)Referred to (?P<committee>.+)', 'committee:referred'),
    Rule(r'(?i)Referred to (?P<committee>.+?)(\.\s+suspense)',
         'committee:referred'),
    Rule(r're-refer to Standing (?P<committee>[^.]+)\.',
         'committee:referred'),

    Rule(r'Read first time\.', 'bill:reading:1'),
    Rule(r'Read second time and amended', 'bill:reading:2'),
    Rule(r'Read third time', 'bill:reading:3'),
    Rule(r'Read third time. Refused passage\.',
         'bill:failed'),
    Rule([r'(?i)read third time.{,5}passed',
          r'(?i)Read third time.+?Passed'],
         ['bill:passed', 'bill:reading:3']),

    Rule(r'Approved by the Governor', 'governor:signed'),
    Rule(r'Approved by the Governor with item veto',
         'governor:vetoed:line-item'),
    Rule('Vetoed by Governor', 'governor:vetoed'),
    Rule(r'To Governor', 'governor:received'),

    Rule(r'amendments concurred in', 'amendment:passed'),
    Rule(r'refused to concur in Assembly amendments', 'amendment:failed'),

    Rule(r'Failed passage in committee', 'committee:failed'),
    Rule(r'(?i)From committee: Do pass', 'committee:passed:favorable'),
    Rule(r'From committee with author\'s amendments', 'committee:passed'),

    # Resolutions
    Rule(r'Adopted', 'bill:passed'),
    Rule(r'Read', 'bill:reading:1'),
    Rule(r'^From committee: Be adopted', 'committee:passed:favorable'),
    )


class CACategorizer(BaseCategorizer):
    rules = _categorizer_rules
