import re
from functools import partial
from collections import namedtuple, defaultdict
from types import MethodType


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

    def __init__(self):
        before_funcs = []
        after_funcs = []
        for name in dir(self):
            attr = getattr(self, name)
            if isinstance(attr, MethodType):
                # func = partial(attr, self)
                func = attr
                if getattr(attr, 'before', None):
                    before_funcs.append(func)
                if getattr(attr, 'after', None):
                    after_funcs.append(func)
        self._before_funcs = before_funcs
        self._after_funcs = after_funcs

    def categorize(self, text):

        whitespace = partial(re.sub, '\s{1,4}', '\s{,4}')

        # Run the before hook.
        text = self.before_categorize(text)
        for func in self._before_funcs:
            text = func(text)

        types = set()
        attrs = defaultdict(set)
        for rule in self.rules:

            for regex in rule.regexes:

                # Try to match the regex.
                m = re.search(whitespace(regex), text)
                if m or (regex in text):
                    # If so, apply its associated types to this action.
                    types |= rule.types

                    # Also add its specified attrs.
                    for k, v in m.groupdict().items():
                        attrs[k].add(v)

                    for k, v in rule.attrs.items():
                        attrs[k].add(v)

                    # Break if the rule says so, otherwise
                    # continue testing against other rules.
                    if rule.stop is True:
                        break

        # Returns types, attrs
        return_val = (list(types), attrs)
        return_val = self.after_categorize(return_val)
        for func in self._after_funcs:
            return_val = func(*return_val)
        return self.finalize(return_val)

    def before_categorize(self, text):
        '''A precategorization hook. Takes/returns text.
        '''
        return text

    def after_categorize(self, return_val):
        '''A post-categorization hook. Takes, returns
        a tuple like (types, attrs), where types is a sequence
        of categories (e.g., bill:passed), and attrs is a
        dictionary of addition attributes that can be used to
        augment the action (or whatever).
        '''
        return return_val

    def finalize(self, return_val):
        '''Before the types and attrs get passed to the
        importer they need to be altered by converting lists to
        sets, etc.
        '''
        types, attrs = return_val
        _attrs = {}

        # Get rid of defaultdict.
        for k, v in attrs.items():

            # Skip empties.
            if not v:
                continue
            else:
                v = filter(None, v)

            # Get rid of sets.
            if isinstance(v, set):
                v = list(v)

            # Some vals should be strings, not seqs.
            if k == 'actor' and len(v) == 1:
                v = v.pop()

            _attrs[k] = v

        return types, _attrs


def after_categorize(f):
    '''A decorator to mark a function to be run
    before categorization has happened.
    '''
    f.after = True
    return f


def before_categorize(f):
    '''A decorator to mark a function to be run
    before categorization has happened.
    '''
    f.before = True
    return f


# These are regex patterns that map to action categories.
_categorizer_rules = (

    # Capture vote tallies.
    Rule(r'-- Needed (?P<vote_threshold>\d+) of \d+ to '
         r'Pass -- Yeas = (?P<yes_votes>\d+), Nays = (?P<no_votes>\d+)'),

    # Misc. capturing rules.
    Rule([r'(?i)motion by (?P<legislators>.+?) to',
          r'(?P<legislators>.+) moved to',
          r'(?P<legislators>.+) spoke for',
          (r'Amendment as offered by (?P<legislators>.+?) '
           r'of (.+?) ((dis)?agreed to|withdrawn)'),
          r'Amendment of (?P<committees>Committee on.+?) agreed to'
          r'Rep. (?P<legislators>.+?) of',
          r'requested by (?P<legislators>.+), Passed',
          r'(?i)floor amendment by (?P<legislators>.+?)( of .+?) (dis)?agreed to',
          r'(?P<legislators>.+?) explained vote',
          r'(?P<committees>Committee on .+?) relieved',
          r'(?P<legislators>.+?) explained vote',
          r'(?i)as moved by (?P<legislators>.+?) of .+',
          (r'(?i)Proposal of amendment\s+by '
           r'Senator\(s\)(?P<legislators>.+?); text'),
          r'submitted by (Rep\.|Senator) (?P<legislators>.+?) for',
          r'on motion of (Rep\.|Senator) (?P<legislators>.+)',
          r'submitted by (Rep\.|Senator) (?P<legislators>.+) for',
          r'Senator(\(s\))? (?P<legislators>.+)',
          r'Remarks of Senator (?P<legislators>[A-Z].+?) journalized',
          r'Senator\(s\) (?P<legislators>.+?) (motion|on|divided)',
          (r'by Senator(\(s\))? (?P<legislators>.+?),? '
            '(&|Passed|on|divided|;|to|Failed|dis)'),
          (r'(by|of) Senator(\(s\))? (?P<legislators>.+?) '
            '(sustained|overruled|journalized)'),
          r'^Senator(\(s\))? (?P<legislators>.+?) [a-z]']),

    # Readings.
    Rule([r'Read First time',
          r'Read 1st time'], 'bill:reading:1'),

    Rule([r'(?i)read 2nd time',
          r'(?i)read second time',
          r'Second Reading'], 'bill:reading:2'),

    Rule(r'(?i)read (third|3rd) time (and|&) passed',
         ['bill:passed', 'bill:reading:3']),

    # Resolutions.
    Rule([r'^(Read (and|&) )?Adopted',
          r'Read 3rd time & adopted',
          r'^Passed on roll call',
          r'^(?i)roll call results passed',
          r'^(?i)roll call.+?passed',
          r'^Passed',
          r'^(?i)(passed|adopted) in concurrence'], 'bill:passed'),

    # Committees.
    Rule([r'(?i)referred to (?P<committees>.+)',
          r'with the report of (?P<committees>Committee on.+?)\s+intact',
          (r'bill (re)?committed to (?P<committees>Committee on.+?)'
            '\b(with|on)\b'),
          r'Committed to( the)? (?P<committees>Committee .+?) (by|with|on)'],
         'committee:referred'),

    Rule([(r'Reported favorably by Senator (?P<legislators>\S+) '
            'for (?P<committees>Committee on .+?), read 2nd time '
            'and 3rd reading ordered'),
          (r'(?i)favorable report( with recommendation of amendment)? '
           r'by (?P<committees>.+)'),
          (r'(?i)Favorable report with proposal of amendment by '
           r'(?P<committees>Committee on .+)')],
         ('committee:passed:favorable', 'bill:reading:2')),

    Rule((r'Reported favorably by Senator (?P<legislators>.+?) '
          r'for (?P<committees>.+?) with recommendation of amendment'),
         'committee:passed:favorable'),

    Rule([(r'(?i)reported without recommendation by( (?P<legislators>'
            'Senator.+?) for)? (?P<committees>.+)'),
           r'proposal of amendment concurred in',
          (r'(?i)proposal of amendment\s+by (?P<committees>Committee '
            'on .+?) agreed to')],
         'committee:passed'),

    Rule(r'Reported favorably by Senator (?P<legislators>.+?) '
         r'for (?P<committees>.+?)', 'committee:passed:favorable'),

    # Amendments
    Rule([r'floor amendment by (.*) agreed to',
          r'motion to amend bill agreed to',
          r'Proposal of amendment agreed to'
          r'Amendment as offered by Rep\.(?P<legislators>.+?) of .+? agreed',
          r'bill amended as moved by Senator\(s\) (?P<legislators>.+)',
          r'Floor Amendment by Rep\. (?P<legislators>.+?) agreed to',
          (r'Recommendation of amendment by (?P<committees>Committee.+?)'
            '(, as amended,)? agreed'),
          (r'Recommendation of amendment by Senator(\(s\))?(?P<legislators>.+?)'
            ' on behalf of (?P<committees>Committee.+) agreed')],
         'amendment:passed'),

    Rule(['Proposal of amendment disagreed to',
          'Motion to amend disagreed to',
          (r'Amendment as offered by Rep\.(?P<legislators>.+?) '
            'of .+? disagreed'),
          r'Floor Amendment by Rep\. (?P<legislators>.+?) disagreed to'],
          'amendment:failed'),

    Rule((r'Amendment as offered by Rep\.(?P<legislators>.+?) '
           'of .+? withdrawn'), 'amendment:withdrawn'),


    # Governor.
    Rule(r'Signed by Governor on .+', 'governor:signed'),
    Rule([r'(?i)Governor vetoed', '(?i)Vetoed by governor'],
         'governor:vetoed', actor='executive'),
    Rule(r'Delivered to the Governor', 'governor:received'),

    )


class Categorizer(BaseCategorizer):
    rules = _categorizer_rules

    @after_categorize
    def split_legislators(self, types, attrs):
        if 'legislators' in attrs:

            legs = []

            for text in attrs['legislators']:
                if text is None:
                    continue
                text = re.sub(r'; text$', '', text)

                # Split.
                _legs = re.split('(?:, |,? and)', text)
                legs.extend(_legs)
            attrs['legislators'] = legs

        return types, attrs
