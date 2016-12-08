import re
from billy.scrape.actions import Rule, BaseCategorizer


# http://www.leg.wa.gov/legislature/pages/committeelisting.aspx#
committees_abbrs = {
    u'AGNR': u'Agriculture & Natural Resources',
    # u'APPE': '',
    # u'APPG': '',
    # u'APPH':
    # u'ARED': '',
    u'AWRD': u'Agriculture, Water & Rural Economic Development',
    u'BFS': u'Business & Financial Services',  # u'Early Learning & K-12 Education',
    u'CB': u'Capital Budget',
    u'CDH': u'Community & Economic Development & Housing',
    u'ED': u'Education',  # u'Education Appropriations & Oversight',
    u'EDTI': u'Economic Development, Trade & Innovation',
    u'EDU': u'Education',
    u'ELHS': u'Early Learning & Human Services',  # u'General Government Appropriations & Oversight',
    u'ENRM': u'Energy, Natural Resources & Marine Waters',
    u'ENV': u'Environment',
    u'ENVI': u'Environment',
    u'EWE': u'Health & Human Services Appropriations & Oversight',
    u'FIHI': u'Financial Institutions, Housing & Insurance',  # u'Health & Long-Term Care',
    u'GO': u'Government Operations, Tribal Relations & Elections',
    u'HCW': u'Health Care & Wellness',
    u'HE': u'Higher Education',
    u'HEA': 'Homeowners\' Association Act',
    u'HEWD': u'Higher Education & Workforce Development',
    u'HSC': u'Human Services & Corrections',
    u'JUD': u'Judiciary',
    u'JUDI': u'Judiciary',
    u'LCCP': u'Labor, Commerce & Consumer Protection',
    u'LG': u'Local Government',
    u'LWD': u'Labor & Workforce Development',
    # u'NRMW': '',
    u'PSEP': u'Public Safety & Emergency Preparedness',
    u'SGTA': u'State Government & Tribal Affairs',
    u'TEC': u'Technology, Energy & Communications',
    u'TR': u'Transportation',
    u'TRAN': u'Transportation',
    u'WAYS': u'Ways & Means'
    }
committee_names = committees_abbrs.values()
committees_rgx = '(%s)' % '|'.join(
    sorted(committee_names, key=len, reverse=True))

# These are regex patterns that map to action categories.
_categorizer_rules = (

    Rule(r'yeas, (?P<yes_votes>\d+); nays, (?P<no_votes>\d+); '
         r'absent, (?P<absent_voters>\d+); excused, (?P<excused_voters>\d+)'),
    Rule(r'Committee on (?P<committees>.+?) at \d'),
    Rule(r'(?P<committees>.+?) relieved of further'),
    Rule(r'Passed to (?P<committees>.+?) for \S+ reading'),
    Rule(r'by (?P<committees>.+?) Committee'),

    Rule(r'^Adopted', 'bill:passed'),
    Rule(r'^Introduced', 'bill:introduced'),
    Rule(r'^Introduced', 'bill:introduced'),
    Rule(r'Third reading, adopted', ['bill:reading:3', 'bill:passed']),

    Rule(r'amendment adopted', 'amendment:passed'),
    Rule(r'amendment not adopted', 'amendment:failed'),
    Rule(r"(?i)third reading, (?P<pass_fail>(passed|failed))", 'bill:reading:3'),
    Rule(r'Read first time', 'bill:reading:1'),
    Rule(r"(?i)first reading, referred to (?P<committees>.*)\.", 'bill:reading:1'),
    Rule(r"(?i)And refer to (?P<committees>.*)", 'committee:referred'),
    Rule(r"(?i).* substitute bill substituted.*", 'bill:substituted'),
    Rule(r"(?i)chapter (((\d+),?)+) \d+ laws.( .+)?", "other"),  # XXX: Thom: Code stuff?
    Rule(r"(?i)effective date \d{1,2}/\d{1,2}/\d{4}.*", "other"),
    Rule(r"(?i)(?P<committees>\w+) - majority; do pass with amendment\(s\) (but without amendments\(s\))?.*\.", "committee:passed:favorable", "committee:passed"),
    Rule(r"(?i)Executive action taken in the (House|Senate) committee on (?P<committees>.*) (at)? .*\.", "other"),
    Rule(r"(?i)(?P<committees>\w+) \- Majority; do pass .* \(Majority Report\)", 'bill:passed'),
    Rule(r"(?i)Conference committee appointed.", "other"),
    Rule(r"(?i)Conference committee report;", 'other'),
    Rule(r"(?i).+ - Majority; \d+.+ substitute bill be substituted, do pass", 'bill:passed'),
    Rule(r"(?i)Signed by (?P<signed_chamber>(Representatives|Senators)) (?P<legislators>.*)", "bill:passed"),
    Rule(r"(?i)Referred to (?P<committees>.*)(\.)?"),
    Rule(r"(?i)(?P<from_committee>.*) relieved of further consideration. On motion, referred to (?P<committees>.*)", 'committee:referred'),
    Rule(r"(?i)Governor partially vetoed", 'governor:vetoed:line-item'),
    Rule(r"(?i)Governor vetoed", 'governor:vetoed'),
    Rule(r"(?i)Governor signed", 'governor:signed'),
    Rule(r"(?i)Passed final passage;", 'bill:passed'),
    Rule(r"(?i)Failed final passage;", 'bill:failed'),
#    Rule(r"(?i)"),
#    Rule(r"(?i)"),
    )


class Categorizer(BaseCategorizer):
    rules = _categorizer_rules

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
