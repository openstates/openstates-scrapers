'''
NY needs an @after_categorize function to expand committee names
and help the importer figure out which committees are being mentioned.
'''
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
        if isinstance(regexes, str):
            regexes = set([regexes])
        regexes = set(regexes or [])

        # Types can be a string or a sequence.
        if isinstance(types, str):
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

        whitespace = partial(re.sub, r'\s{1,4}', r'\\s{,4}')

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
        of categories (e.g., passage), and attrs is a
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

    # Senate passage.
    Rule(r'(?i)^(RE)?PASSED', 'passage'),
    Rule(r'(?i)^ADOPTED', 'passage'),

    # Amended
    Rule(r'(?i)AMENDED (?P<bill_id>\d+)', 'amendment-passage'),
    Rule(r'(?i)AMEND AND RECOMMIT TO (?P<committees>.+)',
         ['amendment-passage', 'referral-committee']),
    Rule(r'(?i)amend .+? and recommit to (?P<committees>.+)',
         ['amendment-passage', 'referral-committee']),
    Rule(r'(?i)AMENDED ON THIRD READING (\(T\) )?(?P<bill_id>.+)',
         'amendment-passage'),
    Rule(r'(?i)print number (?P<bill_id>\d+)', 'amendment-passage'),
    Rule(r'(?i)tabled', 'amendment-deferral'),

    # Committees
    Rule(r'(?i)held .+? in (?P<committees>.+)', 'failure'),
    Rule(r'(?i)REFERRED TO (?P<committees>.+)', 'referral-committee'),
    Rule(r'(?i)reference changed to (?P<committees>.+)',
         'referral-committee'),
    Rule(r'(?i) committed to (?P<committees>.+)', 'referral-committee'),
    Rule(r'(?i)^reported$'),

    # Governor
    Rule(r'(?i)signed chap.(?P<session_laws>\d+)', 'executive-signature'),
    Rule(r'(?i)vetoed memo.(?P<veto_memo>.+)', 'executive-veto'),
    Rule(r'(?i)DELIVERED TO GOVERNOR', 'executive-receipt'),

    # Random.
    Rule(r'(?i)substituted by (?P<bill_id>\w\d+)')
)


class Categorizer(BaseCategorizer):
    rules = _categorizer_rules
