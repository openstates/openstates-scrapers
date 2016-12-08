'''

'''
import re
from billy.scrape.actions import Rule, BaseCategorizer


committees = [
    u"Veterans' Affairs",
    u'Agriculture and Agri-business Committee',
    u'Agriculture',
    u'Banking and Insurance',
    u'Banking',
    u'Children, Juveniles and Other Issues',
    u'Constitutional Revision',
    u'Council of Finance and Administration',
    u'Economic Development and Small Business',
    u'Economic Development',
    u'Education Accountability',
    u'Education',
    u'Employee Suggestion Award Board',
    u'Energy, Industry and Labor',
    u'Energy, Industry and Labor/Economic Development and Small Business',
    u'Enrolled Bills',
    u'Equal Pay Commission',
    u'Finance',
    u'Forest Management Review Commission',
    u'Government and Finance',
    u'Government Operations',
    u'Government Organization',
    u'Health and Human Resources Accountability',
    u'Health and Human Resources',
    u'Health',
    u'Homeland Security',
    u'House Rules',
    u'House Select Committee on Redistricting',
    u'Infrastructure',
    u'Insurance',
    u'Intern Committee',
    u'Interstate Cooperation',
    u'Judiciary',
    u'Law Institute',
    u'Minority Issues',
    u'Natural Resources',
    u'Outcomes-Based Funding Models in Higher Education',
    u'Parks, Recreation and Natural Resources',
    u'PEIA, Seniors and Long Term Care',
    u'Pensions and Retirement',
    u'Political Subdivisions',
    u'Post Audits',
    u'Regional Jail and Correctional Facility Authority',
    u'Roads and Transportation',
    u'Rule-Making Review Committee',
    u'Senior Citizen Issues',
    u'Special Investigations',
    u'Technology',
    u'Veterans Affairs',
    u'Veterans Affairs/ Homeland Security',
    u'Water Resources',
    u'Workforce Investment for Economic Development',
    ]


committees_rgx = '(%s)' % '|'.join(sorted(committees, key=len, reverse=True))


rules = (
    Rule(['Communicated to Senate', 'Senate received',
          'Ordered to Senate'], actor='upper'),
    Rule(['Communicated to House', 'House received',
          'Ordered to House'], actor='lower'),

    Rule('Read 1st time', 'bill:reading:1'),
    Rule('Read 2nd time', 'bill:reading:2'),
    Rule('Read 3rd time', 'bill:reading:3'),
    Rule('Filed for introduction', 'bill:filed'),
    Rule('^Introduced in', 'bill:introduced'),
    Rule(['Passed Senate', 'Passed House'], 'bill:passed'),
    Rule(['Reported do pass', 'With amendment, do pass'], 'committee:passed'),

    Rule([u', but first to .+?; then (?P<committees>[^;]+)',
          u'To (?P<committees>.+?) then']),
    Rule(u'(?i)voice vote', voice_vote=True),
    Rule([u'Amendment rejected'], [u'amendment:failed']),
    Rule([u'To Governor'], [u'governor:received']),
    Rule([u'Passed House'], [u'bill:passed']),
    Rule([u'Read 2nd time'], [u'bill:reading:2']),
    Rule([u', but first to (?P<committees>[^;]+)', u'Rejected'], []),
    Rule([u'Approved by Governor \d{1,2}/\d{1,2}/\d{1,2}$'], [u'governor:signed']),
    Rule([u'^Introduced'], [u'bill:introduced']),
    Rule([u'To .+? then (?P<committees>.+)'], []),
    Rule([u'^Filed for intro'], [u'bill:filed']),
    Rule([u'(?i)referred to (?P<committees>.+)'], [u'committee:referred']),
    Rule(u'Senator (?P<legislators>.+? )requests '
         u'to be removed as sponsor of bill'),
    Rule([u'To House (?P<committees>[A-Z].+)'], [u'committee:referred']),
    Rule([u'Passed Senate'], [u'bill:passed']),
    Rule([u'(?i)committed to (?P<committees>.+?) on'], []),
    Rule([u'Vetoed by Governor'], [u'governor:vetoed']),
    Rule([u'(?i)House concurred in senate amendment'], []),
    Rule([u'Be rejected'], [u'bill:failed']),
    Rule([u'To .+? then (?P<committees>.+) then',
          u'reading to (?P<committees>.+)']),
    Rule([u'Adopted by'], [u'bill:passed']),
    Rule([u'House appointed conferees:  (?P<legislators>.+)'], []),
    Rule([u'Read 3rd time'], [u'bill:reading:3']),
    Rule([u'Be adopted$'], [u'bill:passed']),
    Rule([u'(?i)originating in (House|Senate) (?P<committees>.+)',
          u'(?i)to house (?P<committees>.+)']),
    Rule([u'Read 1st time'], [u'bill:reading:1']),
    Rule([u'To .+? then .+? then (?P<committees>.+)']),
    Rule(r'To %s' % committees_rgx, 'committee:referred')
    )


class Categorizer(BaseCategorizer):
    rules = rules

    def categorize(self, text):
        '''Wrap categorize and add boilerplate committees.
        '''
        attrs = BaseCategorizer.categorize(self, text)
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

                # Strip stuff like "Rules on 1st reading"
                for text in text.split('then'):
                    text = re.sub(r' on .+', '', text)
                    text = text.strip()
                    res.add(text)
        attrs['committees'] = list(res)
        return attrs
