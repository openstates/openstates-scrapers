'''

'''
import re
from billy.scrape.actions import Rule, BaseCategorizer


rules = (
    Rule('^House', actor='lower'),
    Rule('^Senate', actor='upper'),
    Rule('^Governor', actor='governor'),

    Rule('Governor Action - Partial Veto', 'governor:vetoed:line-item'),
    Rule('Sent to the Governor', 'governor:received'),
    Rule('Governor Action - Signed', 'governor:signed'),
    Rule('Governor Action - Vetoed', 'governor:vetoed'),

    Rule(r'^Introduced', 'bill:introduced'),
    Rule(r'Assigned to (?P<committees>.+)'),
    )


class Categorizer(BaseCategorizer):
    rules = rules

    def post_categorize(self, attrs):
        res = set()
        if 'legislators' in attrs:
            for text in attrs['legislators']:
                rgx = r'(,\s+(?![a-z]\.)|\s+and\s+)'
                legs = re.split(rgx, text)
                legs = filter(lambda x: x not in [', ', ' and '], legs)
                res |= set(legs)
        attrs['legislators'] = list(res)

        res = set()
        if 'committees' in attrs:
            for text in attrs['committees'].split('+'):
                res.add(text.strip())
        attrs['committees'] = list(res)
        return attrs
