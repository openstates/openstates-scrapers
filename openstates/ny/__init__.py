import re
import lxml.html
from billy.utils.fulltext import oyster_text, text_after_line_numbers

settings = dict(SCRAPELIB_TIMEOUT=120)

metadata = dict(
    name='New York',
    abbreviation='ny',
    capitol_timezone='America/New_York',
    legislature_name='New York Legislature',
    lower_chamber_name='Assembly',
    upper_chamber_name='Senate',
    lower_chamber_title='Assembly Member',
    upper_chamber_title='Senator',
    lower_chamber_term=2,
    upper_chamber_term=2,
    terms=[dict(name='2011-2012', start_year=2011, end_year=2012,
                sessions=['2011-2012'])],
    session_details={
        '2011-2012': {
            'display_name': '2011 Regular Session',
            '_scraped_name': '2011',
        }
    },
    feature_flags=['subjects', 'events', 'influenceexplorer'],
    _ignored_scraped_sessions=['2009'],

    requests_per_minute=30,
)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://open.nysenate.gov/legislation/advanced/',
                     '//select[@name="session"]/option/text()')

@oyster_text
def extract_text(oyster_doc, data):
    doc = lxml.html.fromstring(data)
    text = doc.xpath('//pre')[0].text_content()
    # if there's a header above a _________, ditch it
    text = text.rsplit('__________', 1)[-1]
    # strip numbers from lines (not all lines have numbers though)
    text = re.sub('\n\s*\d+\s*', ' ', text)
    return text

document_class = dict(
    AWS_PREFIX = 'documents/ny/',
    update_mins = 7*24*60,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
