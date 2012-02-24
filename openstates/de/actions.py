import re
from functools import partial


def get_actor(action_text, chamber, rgxs=(
        (re.compile(r'(in|by) senate', re.I), 'upper'),
        (re.compile(r'(in|by) house', re.I), 'lower'),
        (re.compile(r'by governor', re.I), 'governor'),
        )):
    '''Guess the actor for a particular action.
    '''
    for r, actor in rgxs:
        m = r.search(action_text)
        if m:
            return actor
    return chamber

# ----------------------------------------------------------------------------
# Data for action categorization.

_categories = {

    # Bill is introduced or prefiled
    "bill:introduced": {
        'rgxs': ['^(?i)introduced'],
        'funcs': {},
        },

    # Bill has passed a chamber
    "bill:passed": {
        'rgxs': ['^(?i)passed'],
        'funcs': {},
        },

    # Bill has failed to pass a chamber
    "bill:failed": {
        'rgxs': ['^(?i)defeated'],
        'funcs': {},
        },

    # ???
    # Bill has been withdrawn from consideration
    "bill:withdrawn": {
        'rgxs': [],
        'funcs': {},
        },

    # ???
    # The chamber attempted a veto override and succeeded
    "bill:veto_override:passed": {
        'rgxs': [],
        'funcs': {},
        },

    # ???
    # The chamber attempted a veto override and failed
    "bill:veto_override:failed": {
        'rgxs': [],
        'funcs': {},
        },

    # ???
    # A bill has undergone its first reading
    "bill:reading:1": {
        'rgxs': [],
        'funcs': {},
        },

    # A bill has undergone its second reading
    "bill:reading:2": {
        'rgxs': [],
        'funcs': {},
        },

    # A bill has undergone its third (or final) reading
    "bill:reading:3": {
        'rgxs': [],
        'funcs': {},
        },

    # A bill has been filed (for states where this is a separate event from
    # bill:introduced)
    "bill:filed": {
        'rgxs': [],
        'funcs': {},
        },

    # A bill has been replaced with a substituted wholesale (called hoghousing
    # in some states)
    "bill:substituted": {
        'rgxs': ['(?i)adopted in lieu of'],
        'funcs': {},
        },

    # The bill has been transmitted to the governor for consideration
    "governor:received": {
        'rgxs': [],
        'funcs': {},
        },

    # The bill has signed into law by the governor
    "governor:signed": {
        'rgxs': ['^(?i)signed'],
        'funcs': {},
        },

    # The bill has been vetoed by the governor
    "governor:vetoed": {
        'rgxs': ['^(?i)vetoed'],
        'funcs': {},
        },

    # The governor has issued a line-item (partial) veto
    "governor:vetoed:line-item": {
        'rgxs': [],
        'funcs': {},
        },

    # An amendment has been offered on the bill
    "amendment:introduced": {
        'rgxs': ['^(?i)amendment.{,200}introduced'],
        'funcs': {},
        },

    # The bill has been amended
    "amendment:passed": {
        'rgxs': ['^(?i)amendment.{,200}passed'],
        'funcs': {},
        },

    # An offered amendment has failed
    "amendment:failed": {
        'rgxs': ['^(?i)amendment.{,200}defeated'],
        'funcs': {},
        },

    # An offered amendment has been amended (seen in Texas)
    "amendment:amended": {
        'rgxs': [],
        'funcs': {},
        },

    # ???
    # An offered amendment has been withdrawn
    "amendment:withdrawn": {
        'rgxs': [],
        'funcs': {},
        },

    # An amendment has been 'laid on the table' (generally
    # preventing further consideration)
    "amendment:tabled": {
        'rgxs': ['^(?i)amendment.{,200}laid on table'],
        'funcs': {},
        },

    # The bill has been referred to a committee
    "committee:referred": {
        'rgxs': ['(?i)assigned'],
        'funcs': {},
        },

    # The bill has been passed out of a committee
    "committee:passed": {
        'rgxs': [r'^(?i)reported out of committee'],
        'funcs': {},
        },

    # ??? Looks like this'd require parsing
    # The bill has been passed out of a committee with a favorable report
    "committee:passed:favorable": {
        'rgxs': [],
        'funcs': {},
        },

    # ??? Looks like this'd require parsing
    # The bill has been passed out of a committee with an unfavorable report
    "committee:passed:unfavorable": {
        'rgxs': [],
        'funcs': {},
        },

    # The bill has failed to make it out of committee
    "committee:failed": {
        'rgxs': [],
        'funcs': {},
        },

    # All other actions will have a type of "other"
    }

_funcs = []
append = _funcs.append
for category, data in _categories.items():

    for rgx in data['rgxs']:
        append((category, re.compile(rgx).search))

    for f, args in data['funcs'].items():
        append((category, partial(f, *args)))


def categorize(action, funcs=_funcs):
    '''
    '''
    action = action.strip('" ')
    res = set()
    for category, f in funcs:
        if f(action):
            res.add(category)

    if not res:
        return ('other',)

    return tuple(res)
