import datetime
import lxml.html
from billy.utils.fulltext import text_after_line_numbers
from .bills import IABillScraper
from .legislators import IALegislatorScraper
from .events import IAEventScraper
from .votes import IAVoteScraper


#IA is https but we're getting InsecureRequestWarning on every page
#probably due to an issue with urllib3, so shutting them up for now:
# import urllib3
# urllib3.disable_warnings()


settings = dict(SCRAPELIB_TIMEOUT=240)

metadata = dict(
    name='Iowa',
    abbreviation='ia',
    capitol_timezone='America/Chicago',
    legislature_name='Iowa General Assembly',
    legislature_url='https://www.legis.iowa.gov/',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {
            'name': '2011-2012',
            'start_year': 2011,
            'end_year': 2012,
            'sessions': ['2011-2012'],
        },
        {
            'name': '2013-2014',
            'start_year': 2013,
            'end_year': 2014,
            'sessions': ['2013-2014'],
        },
        {
            'name': '2015-2016',
            'start_year': 2015,
            'end_year': 2016,
            'sessions': ['2015-2016'],
        },
    ],
    session_details={
        '2011-2012': {'display_name': '2011-2012 Regular Session',
                      '_scraped_name': 'General Assembly: 84',
                      'number': '84',
                      'start_date': datetime.date(2011, 1, 10),
                      'end_date': datetime.date(2013, 1, 13),
                     },
        '2013-2014': {'display_name': '2013-2014 Regular Session',
                      '_scraped_name': 'General Assembly: 85',
                      'number': '85', },
        '2015-2016': {'display_name': '2015-2016 Regular Session',
                      '_scraped_name': 'General Assembly: 86',
                      'number': '86', },
    },
    feature_flags=['events', 'influenceexplorer'],
    _ignored_scraped_sessions=['General Assembly: 83', 'General Assembly: 82',
                               'General Assembly: 81', 'General Assembly: 80',
                               'General Assembly: 79', 'General Assembly: 79',
                               'General Assembly: 78', 'General Assembly: 78',
                               'General Assembly: 77', 'General Assembly: 77',
                               'General Assembly: 76', 'General Assembly: 76']
)


def session_list():
    def url_xpath(url, path):
        import requests
        import lxml.html
        doc = lxml.html.fromstring(requests.get(url, verify=False).text)
        return doc.xpath(path)

    import re
    sessions = url_xpath(
        'https://www.legis.iowa.gov/legislation/findLegislation',
        "//section[@class='grid_6']//li/a/text()"
    )
    sessions = [x[0] for x in filter(lambda x: x != [], [
        re.findall("(.*) \(", session)
        for session in sessions
    ])]
    return sessions

def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    text = doc.xpath('//pre')[0].text_content()
    # strip two sets of line numbers
    return text_after_line_numbers(text_after_line_numbers(text))
