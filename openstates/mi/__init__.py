import lxml.html
from billy.utils.fulltext import oyster_text, text_after_line_numbers

settings = dict(SCRAPELIB_TIMEOUT=600)

metadata = {
    'name': 'Michigan',
    'abbreviation': 'mi',
    'capitol_timezone': 'America/New_York',
    'legislature_name': 'Michigan Legislature',
    'lower_chamber_name': 'House',
    'upper_chamber_name': 'Senate',
    'lower_chamber_title': 'Representative',
    'upper_chamber_title': 'Senator',
    'lower_chamber_term': 2,
    'upper_chamber_term': 4,
    'terms': [
        {'name': '2011-2012', 'sessions': ['2011-2012'],
         'start_year': 2011, 'end_year': 2012},
    ],
    'session_details': {
        '2011-2012': {'type':'primary',
                      'display_name': '2011-2012 Regular Session',
                      '_scraped_name': '2011-2012',
                     },
    },
    'feature_flags': ['subjects', 'events', 'influenceexplorer'],
    '_ignored_scraped_sessions': ['2009-2010', '2007-2008', '2005-2006',
                                  '2003-2004', '2001-2002', '1999-2000',
                                  '1997-1998', '1995-1996']

}


def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.legislature.mi.gov/mileg.aspx?'
                     'page=LegBasicSearch', '//option/text()')


@oyster_text
def extract_text(oyster_doc, data):
    doc = lxml.html.fromstring(data)
    text = doc.xpath('//body')[0].text_content()
    return text

document_class = dict(
    AWS_PREFIX = 'documents/mi/',
    update_mins = None,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
