from billy.utils.fulltext import text_after_line_numbers, oyster_text
import lxml.html

metadata = {
    'abbreviation': 'il',
    'name': 'Illinois',
    'legislature_name': 'The Illinois General Assembly',
    'capitol_timezone': 'America/Chicago',
    'lower_chamber_name': 'House',
    'upper_chamber_name': 'Senate',
    'lower_chamber_title': 'Representative',
    'upper_chamber_title': 'Senator',
    'lower_chamber_term': 2,
    'upper_chamber_term': 4, # technically, in every decennial period, one
                             # senatorial term is only 2 years. See
                             # Article IV, Section 2(a) for more information.
    'terms': [
        {'name': '93rd', 'sessions': ['93rd', 'Special_93rd'],
         'start_year': 2003, 'end_year': 2004},
        {'name': '94th', 'sessions': ['94th'],
         'start_year': 2005, 'end_year': 2006},
        {'name': '95th', 'sessions': ['95th', 'Special_95th'],
         'start_year': 2007, 'end_year': 2008},
        {'name': '96th', 'sessions': ['96th', 'Special_96th'],
         'start_year': 2009, 'end_year': 2010},
        {'name': '97th', 'sessions': ['97th'],
         'start_year': 2011, 'end_year': 2012},
    ],
    'feature_flags': [ 'events', 'influenceexplorer' ],
    'session_details': {
        '97th': {'display_name': '97th Regular Session',
                 '_scraped_name': '',
                 'params': { 'GA': '97', 'SessionId': '84' },
                 'speaker': 'Madigan',
                 'president': 'Cullerton',

        },
        '96th': {'display_name': '96th Regular Session',
                 '_scraped_name': '96   (2009-2010)',
                 'params': { 'GA': '96', 'SessionId': '76' },
                 'speaker': 'Madigan',
                 'president': 'Cullerton',

        },
        'Special_96th': {'display_name': '96th Special Session',
                         'params': { 'GA': '96', 'SessionId': '82', 'SpecSess': '1' },
                         'speaker': 'Madigan',
                         'president': 'Cullerton',

        },
        '95th': {'display_name': '95th Regular Session',
                 '_scraped_name': '95   (2007-2008)',
                 'params': { 'GA': '95', 'SessionId': '51' },
                 'speaker': 'Madigan',
                 'president': 'Jones, E.',

        },
        'Special_95th': {'display_name': '95th Special Session',
                         'params': { 'GA': '95', 'SessionId': '52', 'SpecSess': '1' },
                         'speaker': 'Madigan',
                         'president': 'Jones, E.',

        },
        '94th': {'display_name': '94th Regular Session',
                 '_scraped_name': '94   (2005-2006)',
                 'params': { 'GA': '94', 'SessionId': '50' },
                 'speaker': 'Madigan',
                 'president': 'Jones, E.',

        },
        '93rd': {'display_name': '93rd Regular Session',
                 '_scraped_name': '93   (2003-2004)',
                 'params': { 'GA': '93', 'SessionId': '3' },
                 'speaker': 'Madigan',
                 'president': 'Jones, E.',
        },
        'Special_93rd': {'display_name': '93rd Special Session',
                         'params': { 'GA': '93', 'SessionID': '14', 'SpecSess': '1' },
                         'speaker': 'Madigan',
                         'president': 'Jones, E.',
        },
    },
    '_ignored_scraped_sessions': ['92   (2001-2002)',
                                  '91   (1999-2000)',
                                  '90   (1997-1998)',
                                  '89   (1995-1996)',
                                  '88   (1993-1994)',
                                  '87   (1991-1992)',
                                  '86   (1989-1990)',
                                  '85   (1987-1988)',
                                  '84   (1985-1986)',
                                  '83   (1983-1984)',
                                  '82   (1981-1982)',
                                  '81   (1979-1980)',
                                  '80   (1977-1978)',
                                  '79   (1975-1976)',
                                  '78   (1973-1974)',
                                  '77   (1971-1972)']

}

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://ilga.gov/PreviousGA.asp',
                     '//option/text()')

@oyster_text
def extract_text(oyster_doc, data):
    doc = lxml.html.fromstring(data)
    text = ' '.join(x.text_content() for x in doc.xpath('//td[@class="xsl"]'))
    return text

document_class = dict(
    AWS_PREFIX = 'documents/il/',
    update_mins = None,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
