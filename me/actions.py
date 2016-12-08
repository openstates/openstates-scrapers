import re
from billy.scrape.actions import Rule, BaseCategorizer


rules = (
    Rule([(u'(?P<yes_votes>\d+) Yeas - (?P<no_votes>\d+) '
           u'Nays- (?P<excused>\d+) Excused - (?P<absent>\d+) Absent'),
          (u'(?P<yes_votes>\d+) -Yeas, (?P<no_votes>\d+) -Nays, '
           u'(?P<excused>\d+) -Excused, (?P<absent>\d+) -Absent'),
           u'(?P<committees>Committee on .+?) suggested and ordered printed',
          (u'\(Yeas (?P<yes_votes>\d+) - Nays (?P<no_votes>\d+) - Absent '
           u'(?P<absent>\d+) - Excused (?P<excused>\d+)\)( \(Vacancy '
           u'(?P<vacant>\d+)\))?')]),

    Rule([u'Representative (?P<legislators>.+?) of \S+',
          u'Senator (?P<legislators>.+?of \S+)',
          'Representative (?P<legislators>[A-Z]+?( of [A-Za-z]+))',
          u'Senator (?P<legislators>\S+ of \S+)',
          u'Representative [A-Z ]+? of \S+']),

    Rule(u'REFERRED to the (?P<committees>Committee on [A-Z ]+(?![a-z]))',
         'committee:referred'),
    Rule(['READ A SECOND TIME'], ['bill:reading:2']),
    Rule(['(?i)read once'], ['bill:reading:1']),
    Rule('(?i)finally passed', 'bill:passed'),
    Rule('(?i)passed to be enacted', 'bill:passed'),
    Rule('COMMITTED to the (?P<committees>Committee on .+?)\.',
         'committee:referred'),
    Rule(r'VETO was NOT SUSTAINED', 'bill:veto_override:passed'),
    Rule(r'VETO was SUSTAINED', 'bill:veto_override:failed'),
    Rule(r'(?<![Aa]mendment)READ and (PASSED|ADOPTED)(, in concurrence)?\.$',
            'bill:passed')
    )


class Categorizer(BaseCategorizer):
    rules = rules

    def categorize(self, text):
        '''Wrap categorize and add boilerplate committees.
        '''
        attrs = BaseCategorizer.categorize(self, text)
        committees = attrs['committees']
        for committee in re.findall(committees_rgx, text):
            if committee not in committees:
                committees.append(committee)
        return attrs

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

committees = [
    u'AGRICULTURE, CONSERVATION AND FORESTRY',
    u'APPROPRIATIONS AND FINANCIAL AFFAIRS',
    u'CRIMINAL JUSTICE AND PUBLIC SAFETY',
    u'EDUCATION AND CULTURAL AFFAIRS',
    u'ENERGY, UTILITIES AND TECHNOLOGY',
    u'ENVIRONMENT AND NATURAL RESOURCES',
    u'HEALTH AND HUMAN SERVICES',
    u'INLAND FISHERIES AND WILDLIFE',
    u'INSURANCE AND FINANCIAL SERVICES',
    u'JOINT RULES',
    u'JUDICIARY',
    u'LABOR, COMMERCE, RESEARCH AND ECONOMIC DEVELOPMENT',
    u'MARINE RESOURCES',
    u'REGULATORY FAIRNESS AND REFORM',
    u'STATE AND LOCAL GOVERNMENT',
    u'TAXATION',
    u'TRANSPORTATION',
    u'VETERANS AND LEGAL AFFAIRS',
    ]
committees_rgx = '(%s)' % '|'.join(sorted(committees, key=len, reverse=True))
