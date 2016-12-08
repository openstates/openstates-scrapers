import re
from billy.scrape.actions import Rule, BaseCategorizer

# These are regex patterns that map to action categories.
_categorizer_rules = (

    # Capture some groups.
    Rule(r'Senators (?P<legislators>.+) a committee of conference'),
    Rule(r"(?P<version>Printer's No. \d+)"),

    Rule(r'(?i)introduced', 'bill:introduced'),

    # Committee referred, reported.
    Rule(r"Referred to (?P<committees>.+)", 'committee:referred'),
    Rule(r"Re-(referred|committed) to (?P<committees>.+)",
         'committee:referred'),
    Rule(r'(?i)(re-)?reported', 'committee:passed'),
    Rule(r'Reported with request to re-refer to (?P<committees>.+)',
         ['committee:referred', 'committee:passed']),

    Rule([r'^Amended on', r'as amended'], 'amendment:passed'),

    # Governor.
    Rule(r'^Approved by the Governor', 'governor:signed'),
    Rule(r'^Presented to the Governor', 'governor:received'),

    # Passage.
    Rule([r'^Final passage', '^Third consideration and final passage'],
         'bill:passed'),
    Rule(r'(?i)adopted', 'bill:passed'),
    Rule(r'^First consideration', 'bill:reading:1'),
    Rule(r'Second consideration', 'bill:reading:2'),
    Rule(r'Third consideration', 'bill:reading:3'),
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
