import re
from billy.scrape.actions import Rule, BaseCategorizer

# These are regex patterns that map to action categories.
_categorizer_rules = (

    Rule(r'Ayes:\s+(?P<yes_votes>\d+)\s+Nays:\s+(?P<no_votes>\d+)'),

    Rule([u'Introduced'], [u'bill:introduced']),
    Rule([u'Adopted'], [u'bill:passed']),
    Rule([u'HAs rejected'], [u'amendment:failed']),
    Rule(u'(?i)Measure.+?passed', 'bill:passed'),
    Rule(u'(?i)Measure.+?passed', 'bill:passed'),
    Rule(u'Third Reading, Measure passed',
         ['bill:passed', 'bill:reading:3']),

    Rule([u'^Amendment withdrawn'], [u'amendment:withdrawn']),
    Rule([u'^Amended$'], [u'amendment:passed']),
    Rule([u'^Amendment failed'], [u'amendment:failed']),
    Rule([u'^Amendment restore'], [u'amendment:passed']),

    Rule('First Reading', ('bill:introduced', 'bill:reading:1')),
    Rule([u'Second Reading referred to (?P<committees>.+)'],
         [u'committee:referred', u'bill:reading:2']),
    Rule([u'Second Reading referred to (?P<committees>.+? Committee)'],
         [u'committee:referred', u'bill:reading:2']),
    Rule([u'Second Reading referred to .+? then to (?P<committees>.+)'],
         [u'committee:referred', u'bill:reading:2']),
    Rule([u'Second Reading referred to (?P<committees>.+?) then to '],
         [u'committee:referred', u'bill:reading:2']),
    Rule([u'Second Reading referred to .+? then to (?P<committees>.+)'],
         [u'committee:referred', u'bill:reading:2']),
    Rule([u'(?i)Placed on Third Reading'], [u'bill:reading:3']),
    Rule([u'^(?i)Third Reading'], [u'bill:reading:3']),

    Rule([u'Do Pass (as amended )?(?P<committees>.+)'], [u'committee:passed']),
    Rule([u'Failed in Committee - (?P<committees>.+)'], [u'committee:failed']),
    Rule([u'CR; Do not pass (?P<committees>)'], [u'committee:failed']),
    Rule([u'rereferred to (?P<committees>.+)'], [u'committee:referred']),
    Rule([u'Referred to (?P<committees>.+?)'], [u'committee:referred']),
    Rule([u'Reported Do Pass, amended by committee substitute (?P<committees>.+?);'],
    Rule([u'^(?i)Reported Do Pass'], [u'committee:passed']),
    Rule([u'Do pass, amended by committee substitute (?P<committees>)'],
         [u'committee:passed']),

    Rule([u'Sent to Governor'], [u'governor:received'], actor='governor'),
    Rule([u'^(Signed|Approved) by Governor'], [u'governor:signed'], actor='governor'),
    Rule([u'^Vetoed'], [u'governor:vetoed'], actor='governor'),
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
