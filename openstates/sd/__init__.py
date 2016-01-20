import datetime
import scrapelib
import lxml.html
from .bills import SDBillScraper
from .legislators import SDLegislatorScraper

settings = dict(
    SCRAPELIB_RPM=8,
    SCRAPELIB_RETRY_WAIT=30,
)

metadata = dict(
    name = 'South Dakota',
    abbreviation = 'sd',
    legislature_name = 'South Dakota State Legislature',
    legislature_url = 'http://legis.state.sd.us/',
    capitol_timezone = 'America/Chicago',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms = [
        {
            'name': '2009-2010',
            'start_year': 2009,
            'end_year': 2010,
            'sessions': ['2009', '2010']
        },
        {
            'name': '2011-2012',
            'start_year': 2011,
            'end_year': 2012,
            'sessions': ['2011', '2011s', '2012']
        },
        {
            'name': '2013-2014',
            'start_year': 2013,
            'end_year': 2014,
            'sessions': ['2013', '2014']
        },
        {
            'name': '2015-2016',
            'start_year': 2015,
            'end_year': 2016,
            'sessions': ['2015', '2016']
        },
    ],
    session_details = {
        '2009': {
            'display_name': '2009 Regular Session',
            '_scraped_name': '2009 (84th) Session',
        },
        '2010': {
            'display_name': '2010 Regular Session',
            '_scraped_name': '2010 (85th) Session',
        },
        '2011': {
            'start_date': datetime.date(2011, 1, 11),
            'display_name': '2011 Regular Session',
            '_scraped_name': '2011 (86th) Session',
        },
        '2011s': {
            'display_name': '2011 Special Session',
            '_scraped_name': '2011 (86th) Special Session',
        },
        '2012': {
            'display_name': '2012 Regular Session',
            '_scraped_name': '2012 (87th) Session',
        },
        '2013': {
            'display_name': '2013 Regular Session',
            '_scraped_name': '2013 (88th) Session',
        },
        '2014': {
            'display_name': '2014 Regular Session',
            '_scraped_name': '2014 (89th) Session',
        },
        '2015': {
            'display_name': '2015 Regular Session',
            '_scraped_name': '2015 (90th) Session',
        },
        '2016': {
            'display_name': '2016 Regular Session',
            '_scraped_name': '2016 (91st) Session',
        },
    },
    feature_flags = ['subjects', 'influenceexplorer'],
    _ignored_scraped_sessions = [
        '2016 (91st) Session',
        'Previous Years',
    ],
)


def session_list():
    html = scrapelib.Scraper().get('http://legis.sd.gov/Legislative_Session/'
        'Menu.aspx').text
    doc = lxml.html.fromstring(html)
    sessions = doc.xpath('//div[@id="ContentPlaceHolder1_BlueBoxLeft"]//ul/li'
        '/a/div/text()')
    return sessions


def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    return ' '.join(div.text_content() for div in
        doc.xpath('//div[@align="full"]'))
