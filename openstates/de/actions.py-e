import re
from openstates.utils.actions import Rule, BaseCategorizer


rules = (
    Rule([u'Amendment (?P<bills>.+?) -\s+Laid On Table'], ['amendment-deferral']),
    Rule([u'Favorable'], ['committee-passage-favorable']),
    Rule([u'(?i)Amendment (?P<bills>.+?) defeated'], ['amendment-failure']),
    Rule([u'(?i)introduced and adopted in lieu of (?P<bills>.+)'],
         ['introduction']),
    Rule([u'(?i)assigned to (?P<committees>.+?) Committee in'],
         ['referral-committee', 'introduction']),
    Rule([u'Signed by Governor'], ['executive-signature']),
    Rule([u'(?i)Amendment (?P<bills>[\w\s]+?) Introduced'],
         ['amendment-introduction']),
    Rule([u'Amendment (?P<bills>.+?) -  Passed'], ['amendment-passage']),
    Rule([u'^Passed by'], ['passage']),
    Rule([u'^Defeated'], ['failure']),
    Rule([u'(?i)unfavorable'], ['committee-passage-unfavorable']),
    Rule([u'Reported Out of Committee \((?P<committees>.+?)\)'],
         ['committee-passage']),
    Rule([u'Vetoed by Governor'], ['executive-veto']),
    Rule([u'(?i)Amendment (?P<bills>.+?)\s+-\s+Introduced'],
         ['amendment-introduction']),
    Rule([u'(?i)Amendment (?P<bills>[\w\s]+?) Passed'], ['amendment-passage']),
    Rule([u'Amendment (?P<bills>.+?) -  Defeated by House of .+?\. Votes: Defeated'],
         ['amendment-failure']),
    Rule([u'^Introduced'], ['introduction']),
    Rule([u'Amendment (?P<bills>.+?) -  Defeated in House'], ['amendment-failure']),
    Rule([u'^Passed in House'], ['passage'])
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
