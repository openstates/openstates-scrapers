import re
from billy.scrape.actions import Rule, BaseCategorizer

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
    Rule(r'(House|Senate) sponsors?:\s+Senators\s+(?P<legislators>.+)'),
    Rule(r'Senators (?P<legislators>.+?) added as (?:co)?sponsors'),
    Rule('(?i)(co)?sponsors: (?P<legislators>.+)'),

    # Amendments.
    Rule((r'(?P<version>Amendment \d+)\s+\(\s*(?P<legislators>.+?)\)'
          r'.+?prevailed'), 'amendment:passed'),
    Rule(r'(?i)(house|senate) concurred in (house|senate) amendments',
         'amendment:passed'),
    Rule(r'Senate sponsors: Senators (?P<legislators>.+)'),

    # Readings.
    Rule(r'(?i)^first reading:', ('bill:introduced', 'bill:reading:1')),
    Rule(r'(?i)^second reading:', 'bill:reading:2'),
    Rule(r'(?i)^third reading:', 'bill:reading:3'),

    # Committees.
    Rule(r'Committee report:.+?do pass', 'committee:passed:favorable'),
    Rule([r'(?i)referred to (?P<committees>.+)',
          r'(?i)reassigned to (?P<committees>.+)'], 'committee:referred'),
    Rule(r'(?i)Committee report:.*?do pass', 'committee:passed:favorable'),
    Rule(r'(?i)motion to recommit to (?P<committees>.+?)'
         r'\((?P<legislators>.+?)\)'),

    # Passage/failure.
    Rule(r'passed', 'bill:passed'),
    Rule(r'reading:\s+adopted', 'bill:passed'),
    Rule(r'(?i)Third reading: passed', 'bill:passed'),

    # Weird.
    Rule(r'Conference committee.+adopted',
         ['committee:passed', 'amendment:passed']),

    # Governor.
    Rule(r'Signed by the Governor', 'governor:signed'),
    )


class Categorizer(BaseCategorizer):
    rules = _categorizer_rules

    def post_categorize(self, attrs):
        res = set()
        if 'legislators' in attrs:
            for text in attrs['legislators']:
                rgx = r'(,\s+(?![a-z]\.)|\s+and\s+)'
                legs = re.split(rgx, text)
                legs = filter(lambda x: x not in [', ', ' and '], legs)
                res |= set(legs)
        attrs['legislators'] = list(res)
        return attrs
