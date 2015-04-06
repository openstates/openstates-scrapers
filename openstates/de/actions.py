import re
from billy.scrape.actions import Rule, BaseCategorizer


rules = (
    Rule([u'Amendment (?P<bills>.+?) -\s+Laid On Table'], ['amendment:tabled']),
    Rule([u'Favorable'], ['committee:passed:favorable']),
    Rule([u'(?i)Amendment (?P<bills>.+?) defeated'], ['amendment:failed']),
    Rule([u'(?i)introduced and adopted in lieu of (?P<bills>.+)'],
         ['bill:introduced']),
    Rule([u'(?i)assigned to (?P<committees>.+?) Committee in'],
         ['committee:referred', 'bill:introduced']),
    Rule([u'Signed by Governor'], ['governor:signed']),
    Rule([u'(?i)Amendment (?P<bills>[\w\s]+?) Introduced'],
         ['amendment:introduced']),
    Rule([u'Amendment (?P<bills>.+?) -  Passed'], ['amendment:passed']),
    Rule([u'^Passed by'], ['bill:passed']),
    Rule([u'^Defeated'], ['bill:failed']),
    Rule([u'(?i)unfavorable'], ['committee:passed:unfavorable']),
    Rule([u'Reported Out of Committee \((?P<committees>.+?)\)'],
         ['committee:passed']),
    Rule([u'Vetoed by Governor'], ['governor:vetoed']),
    Rule([u'(?i)Amendment (?P<bills>.+?)\s+-\s+Introduced'],
         ['amendment:introduced']),
    Rule([u'(?i)Amendment (?P<bills>[\w\s]+?) Passed'], ['amendment:passed']),
    Rule([u'Amendment (?P<bills>.+?) -  Defeated by House of .+?\. Votes: Defeated'],
         ['amendment:failed']),
    Rule([u'^Introduced'], ['bill:introduced']),
    Rule([u'Amendment (?P<bills>.+?) -  Defeated in House'], ['amendment:failed']),
    Rule([u'^Passed in House'], ['bill:passed'])
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
            for text in attrs['committees']:
                text = text.strip()
                res.add(text)
        attrs['committees'] = list(res)
        return attrs


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