from billy.utils.fulltext import oyster_text
import lxml.html

metadata = {
    'abbreviation': 'nh',
    'name': 'New Hampshire',
    'capitol_timezone': 'America/New_York',
    'legislature_name': 'New Hampshire General Court',
    'upper_chamber_name': 'Senate',
    'lower_chamber_name': 'House',
    'upper_chamber_title': 'Senator',
    'lower_chamber_title': 'Representative',
    'upper_chamber_term': 2,
    'lower_chamber_term': 2,
    'terms': [
        {'name': '2011-2012', 'sessions': ['2011', '2012'],
         'start_year': 2011, 'end_year': 2012}
    ],
    'session_details': {
        '2011': {'display_name': '2011 Regular Session',
                 'zip_url': 'http://gencourt.state.nh.us/downloads/2011%20Session%20Bill%20Status%20Tables.zip',
                 '_scraped_name': '2011 Session',
                },
        '2012': {'display_name': '2012 Regular Session',
                 'zip_url': 'http://gencourt.state.nh.us/downloads/2012%20Session%20Bill%20Status%20Tables.zip',
                 '_scraped_name': '2012 Session',
                },
    },
    'feature_flags': ['influenceexplorer'],
}

def session_list():
    from billy.scrape.utils import url_xpath
    zips = url_xpath('http://gencourt.state.nh.us/downloads/',
                     '//a[contains(@href, "Bill%20Status")]/text()')
    return [zip.replace(' Bill Status Tables.zip', '') for zip in zips]

@oyster_text
def extract_text(oyster_doc, data):
    doc = lxml.html.fromstring(data)
    return doc.xpath('//html')[0].text_content()

document_class = dict(
    AWS_PREFIX = 'documents/nh/',
    update_mins = 7*24*60,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
