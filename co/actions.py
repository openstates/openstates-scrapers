'''

'''
import re
from billy.scrape.actions import Rule, BaseCategorizer


committees = [
    u'Agriculture, Livestock (?:and|&) Natural Resources',
    u'Finance',
    u'Joint Budget Committee',
    u'Appropriations',
    u'Health (?:and|&) Environment',
    u'Transportation',
    u'Education',
    u'Agriculture, Livestock, (?:and|&) Natural Resources',
    u'Judiciary',
    u'Legal Services',
    u'State, Veterans (?:and|&) Military Affairs',
    u'Economic (?:and|&) Business Development',
    u'Local Government',
    u'Congressional Redistricting',
    u'Legislative Council',
    u'State Veterans, (?:and|&) Military Affairs',
    u'Health (?:and|&) Environment',
    u'Legislative Audit',
    u'Capital Development',
    u'State, Veterans, (?:and|&) Military Affairs',
    u'State, Veterans, (?:and|&) Military Affairs',
    u'Executive Committee of Legislative Council',
    u'Health (?:and|&) Environment',
    u'Finance',
    u'Appropriations',
    u'Agriculture, Natural Resources (?:and|&) Energy',
    u'Judiciary',
    u'Business, Labor (?:and|&) Technology',
    u'Health (?:and|&) Human Services',
    u'State, Veterans (?:and|&) Military Affairs',
    u'Local Government',
    u'Legislative Audit',
    u'Executive Committee of Legislative Council',
    u'Transportation',
    u'Health (?:and|&) Human Services',
    u'Education',
    u'Legislative Council',
    u'Legal Services',
    u'Capital Development',
    u'Transportation (?:and|&) Energy',
    u'Joint Budget Committee',
    u'Business, Labor, (?:and|&) Technology',
    u'State, Veterans, (?:and|&) Military Affairs'
    ]


rules = (
    Rule('^House', actor='lower'),
    Rule('^Senate', actor='upper'),
    Rule('^Introduced in Senate', actor='upper'),
    Rule('^Introduced in House', actor='lower'),
    Rule('^Governor', actor='governor'),

    Rule('Governor Action - Partial Veto', 'governor:vetoed:line-item'),
    Rule('Sent to the Governor', 'governor:received'),
    Rule('Governor Action - Signed', 'governor:signed'),
    Rule('Governor Signed', 'governor:signed'),
    Rule('Governor Action - Vetoed', 'governor:vetoed'),

    Rule(r'^Introduced', 'bill:introduced'),
    Rule(r'Assigned to (?P<committees>.+)'),

    Rule(u'(?i)refer (un)?amended to (?P<committees>.+)',
         [u'committee:referred']),
    Rule(u'(?i)\S+ Committee on (?P<committees>.+?) Refer (un)amended'),
    Rule(u'Second Reading Passed', [u'bill:reading:2']),
    Rule(u'Third Reading Passed', ['bill:reading:3', 'bill:passed'])
    )

committees_rgx = '(%s)' % '|'.join(
    sorted(committees, key=len, reverse=True))


class Categorizer(BaseCategorizer):
    rules = rules

    def categorize(self, text):
        '''Wrap categorize and add boilerplate committees.
        '''
        attrs = BaseCategorizer.categorize(self, text)
        if 'committees' in attrs:
            committees = attrs['committees']
            for committee in re.findall(committees_rgx, text, re.I):
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
                for committee in text.split(' + '):
                    res.add(committee.strip())
        attrs['committees'] = list(res)
        return attrs
