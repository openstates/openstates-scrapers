'''

'''
import re
from billy.scrape.actions import Rule, BaseCategorizer


committees = [
    u'LEGISLATIVE FINANCE COMMITTEE COMMITTEE',
    u'NEW MEXICO FINANCE AUTHORITY OVERSIGHT COMMITTEE COMMITTEE',
    u'APPROPRIATIONS and FINANCE COMMITTEE',
    u'TRANSPORTATION and PUBLIC WORKS COMMITTEE',
    u'PRINTING and SUPPLIES COMMITTEE',
    u'LAND GRANT COMMITTEE COMMITTEE',
    u'LEGISLATIVE HEALTH and HUMAN SERVICES COMMITTEE COMMITTEE',
    u'LEGISLATIVE EDUCATION STUDY COMMITTEE COMMITTEE',
    u'LABOR and HUMAN RESOURCES COMMITTEE',
    u'HEALTH and GOVERNMENT AFFAIRS COMMITTEE',
    u'WATER and NATURAL RESOURCES COMMITTEE COMMITTEE',
    u'ENERGY and NATURAL RESOURCES COMMITTEE',
    u'JUDICIARY COMMITTEE',
    u'MORTGAGE FINANCE AUTHORITY ACT OVERSIGHT COMMITTEE COMMITTEE',
    u'ENROLLING and ENGROSSING - A COMMITTEE',
    u'COURTS, CORRECTIONS and JUSTICE COMMITTEE COMMITTEE',
    u'RULES and ORDER OF BUSINESS COMMITTEE',
    u'AGRICULTURE and WATER RESOURCES COMMITTEE',
    u'ECONOMIC and RURAL DEVELOPMENT COMMITTEE COMMITTEE',
    u'BUSINESS and INDUSTRY COMMITTEE',
    u'ENROLLING and ENGROSSING - B COMMITTEE',
    u'INVESTMENTS and PENSIONS OVERSIGHT COMMITTEE COMMITTEE',
    u'REVENUE STABILIZATION and TAX POLICY COMMITTEE COMMITTEE',
    u'VOTERS and ELECTIONS COMMITTEE',
    u'SCIENCE, TECHNOLOGY and TELECOMMUNICATIONS COMMITTEE COMMITTEE',
    u'TOBACCO SETTLEMENT REVENUE OVERSIGHT COMMITTEE COMMITTEE',
    u'RADIOACTIVE and HAZARDOUS MATERIALS COMMITTEE COMMITTEE',
    u'EDUCATION COMMITTEE',
    u'TAXATION and REVENUE COMMITTEE',
    u"MILITARY and VETERANS' AFFAIRS COMMITTEE",
    u'CAPITOL BUILDINGS PLANNING COMMISSION COMMITTEE',
    u'LEGISLATIVE COUNCIL COMMITTEE',
    u'PUBLIC SCHOOL CAPITAL OUTLAY OVERSIGHT TASK FORCE COMMITTEE',
    u'INDIAN AFFAIRS COMMITTEE COMMITTEE',
    u'CONSUMER and PUBLIC AFFAIRS COMMITTEE',
    u'INTERIM LEGISLATIVE ETHICS COMMITTEE COMMITTEE',
    u'DISABILITIES CONCERNS SUBCOMMITTEE COMMITTEE',
    u'BEHAVIORAL HEALTH SUBCOMMITTEE COMMITTEE',
    u'INVESTIGATORY SUBCOMMITTEE OF THE RULES and ORDER OF BUSINESS SUBCOMMITTEE COMMITTEE',
    u'CORPORATIONS and TRANSPORTATION COMMITTEE',
    u'FINANCE COMMITTEE',
    u'PUBLIC AFFAIRS COMMITTEE',
    u"COMMITTEES' COMMITTEE",
    u'CONSERVATION COMMITTEE',
    u'INDIAN and CULTURAL AFFAIRS COMMITTEE',
    u'SENATE RULES COMMITTEE',
    ]

committees_rgx = '(%s)' % '|'.join(sorted(committees, key=len, reverse=True))


rules = (
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
