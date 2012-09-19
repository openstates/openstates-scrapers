import datetime
import lxml.html
from billy.utils.fulltext import oyster_text, text_after_line_numbers

settings = dict(
    SCRAPELIB_TIMEOUT=600,
    SCRAPELIB_RPM=30
)

metadata = {
    'capitol_timezone': 'America/New_York',
    'lower_chamber_title': 'Representative',
    'lower_chamber_name': 'House',
    'upper_chamber_title': 'Senator',
    'terms': [
        {
            'end_year': 2010,
            'start_year': 2009,
            'name': '186',
            'sessions': [ '186th' ]
        },
        {
            'end_year': 2012,
            'start_year': 2011,
            'name': '187',
            'sessions': [ '187th' ]
        }
    ],
    'name': 'Massachusetts',
    'upper_chamber_term': 2,
    'abbreviation': 'ma',
    'upper_chamber_name': 'Senate',
    'session_details': {
        '186th': {
            'type': 'primary',
            'display_name': '186th Legislature',
            '_scraped_name': '186th',
        },
        '187th': {
            'type': 'primary',
            'display_name': '187th Legislature',
            '_scraped_name': '187th',
        }
    },
    'legislature_name': 'Massachusetts General Court',
    'lower_chamber_term': 2,
    'feature_flags': ['events', 'influenceexplorer'],
}

def session_list():
    import re
    from billy.scrape.utils import url_xpath
    sessions = url_xpath('http://www.malegislature.gov/Bills/Search',
        "//select[@id='Input_GeneralCourtId']/option/text()")
    # Ok, this is actually a mess. Let's clean it up.
    # sessions.remove('--Select Value--')  # They removed this.
    sessions = [ re.sub("\(.*$", "", session).strip() for session in sessions ]
    return sessions


@oyster_text
def extract_text(oyster_doc, data):
    doc = lxml.html.fromstring(data)
    text = ' '.join([x.text_content()
                     for x in doc.xpath('//td[@class="longTextContent"]//p')])
    return text

document_class = dict(
    AWS_PREFIX = 'documents/ma/',
    update_mins = 7*24*60,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
