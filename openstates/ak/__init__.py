import lxml.html
from billy.utils.fulltext import text_after_line_numbers

settings = dict(SCRAPELIB_TIMEOUT=600)

metadata = dict(
    name='Alaska',
    capitol_timezone='America/Anchorage',
    abbreviation='ak',
    legislature_name='Alaska State Legislature',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        dict(name='26', sessions=['26'],
             start_year=2009, end_year=2010),
        dict(name='27', sessions=['27'],
             start_year=2011, end_year=2012),
        dict(name='28', sessions=['28'],
             start_year=2013, end_year=2014),
    ],
    session_details={
        '26': {'display_name': '26th Legislature',
               '_scraped_name': 'The 26th Legislature (2009-2010)'},
        '27': {'display_name': '27th Legislature',
               '_scraped_name': 'The 27th Legislature (2011-2012)'},
        '28': {'display_name': '28th Legislature',
               '_scraped_name': 'The 28th Legislature (2013-2014)'},
    },
    _ignored_scraped_sessions=['The 25th Legislature (2007-2008)',
                               'The 24th Legislature (2005-2006)',
                               'The 23rd Legislature (2003-2004)',
                               'The 22nd Legislature (2001-2002)',
                               'The 21st Legislature (1999-2000)',
                               'The 20th Legislature (1997-1998)',
                               'The 19th Legislature (1995-1996)',
                               'The 18th Legislature (1993-1994)'],
    feature_flags=['subjects', 'influenceexplorer'],
)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.legis.state.ak.us/basis/start.asp',
                     '(//ul)[last()]/li/a/nobr/text()')

def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    text = doc.xpath('//pre')[0].text_content()
    text = text_after_line_numbers(text)
    return text
