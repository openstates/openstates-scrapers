import re
from billy.scrape.actions import Rule, BaseCategorizer

# These are regex patterns that map to action categories.
_categorizer_rules = (
    Rule(r'(?i)(co)?authored by (?P<legislators>.+)'),
    Rule(r'(?i)Representative\(s\) (?P<legislators>.+)'),
    Rule(r'Ayes:\s+(?P<yes_votes>\d+)\s+Nays:\s+(?P<no_votes>\d+)'),
    Rule(r'(?i)SCs named (?P<legislators>.+)'),
    Rule(r'(?i)remove as author (?P<legislators>.+);'),
    # Rule('First Reading', ['bill:introduced', 'bill:reading:1']),
    # Rule('Sent to Governor', ['governor:received']),
    # Rule('(?i)referred to', ['committee:referred']),
    # Rule('Second Reading', ['bill:reading:2']),
    # Rule('Third Reading', ['bill:reading:3']),
    # Rule('Reported Do Pass', ['committee:passed']),
    # Rule('(Signed|Approved) by Governor', ['governor:signed']),
    # Rule('(?i)measure passed', ['bill:passed']),
    )


class Categorizer(BaseCategorizer):
    rules = _categorizer_rules

    def post_categorize(self, attrs):
        res = set()
        if 'legislators' in attrs:
            for text in attrs['legislators']:
                text = text.replace('Representative(s)', '')
                text = text.replace('(principal House author) ', '')
                rgx = r'(,\s+(?![a-z]\.)|\s+and\s+)'
                legs = re.split(rgx, text)
                legs = filter(lambda x: x not in [', ', ' and '], legs)
                res |= set(legs)
        attrs['legislators'] = list(res)

        res = set()
        if 'committees' in attrs:
            for text in attrs['committees']:
                text = text.replace('by committee substitute', '')
                text = text.replace('CR filed;', '')
                text = text.strip()
                res.add(text)
        attrs['committees'] = list(res)
        return attrs
