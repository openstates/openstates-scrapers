import datetime
from billy.utils.fulltext import pdfdata_to_text, text_after_line_numbers
from .bills import NDBillScraper
from .legislators import NDLegislatorScraper
from .committees import NDCommitteeScraper
from .votes import NDVoteScraper

metadata = dict(
    name = 'North Dakota',
    abbreviation = 'nd',
    legislature_name = 'North Dakota Legislative Assembly',
    legislature_url='http://www.legis.nd.gov/',
    capitol_timezone='America/North_Dakota/Center',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms = [
        {'name': '62', 'sessions': ['62'],
         'start_year': 2011, 'end_year': 2012},
        {'name': '63', 'sessions': ['63'],
         'start_year': 2013, 'end_year': 2014},
        {'name': '64', 'sessions': ['64'],
         'start_year': 2015, 'end_year': 2016},
    ],
    session_details={
        '62' : {'start_date' : datetime.date(2011, 1, 4),
                'display_name' : '62nd Legislative Assembly (2011-2012)',
                '_scraped_name': '62nd Legislative Assembly (2011-12)',
               },
        '63' : {'start_date': datetime.date(2013, 1, 8),
                'display_name' : '63rd Legislative Assembly (2013-2014)',
                '_scraped_name': '63rd Legislative Assembly (2013-14)',
               },
        '64' : {'start_date': datetime.date(2015, 1, 8),
                'display_name' : '64th Legislative Assembly (2015-2016)',
                '_scraped_name': '64th Legislative Assembly (2015-16)',
               },
    },
    feature_flags=['influenceexplorer'],
    _ignored_scraped_sessions=[
        # Nothing is available for the 65th yet, and 64th events are ongoing
        '65th Legislative Assembly (2017-18)',

        '61st Legislative Assembly (2009-10)',
        '60th Legislative Assembly (2007-08)',
        '59th Legislative Assembly (2005-06)',
        '58th Legislative Assembly (2003-04)',
        '57th Legislative Assembly (2001-02)',
        '56th Legislative Assembly (1999-2000)',
        '55th Legislative Assembly (1997-98)',
        '54th Legislative Assembly (1995-96)',
        '53rd Legislative Assembly (1993-94)',
        '52nd Legislative Assembly (1991-92)',
        '51st Legislative Assembly (1989-90)',
        '50th Legislative Assembly (1987-88)',
        '49th Legislative Assembly (1985-86)'
    ]
)

def session_list():
    import scrapelib
    import lxml.html

    url = 'http://www.legis.nd.gov/assembly/'
    html = scrapelib.Scraper().get(url).text
    doc = lxml.html.fromstring(html)
    doc.make_links_absolute(url)
    return doc.xpath("//div[@class='view-content']//a/text()")


def extract_text(doc, data):
    return text_after_line_numbers(pdfdata_to_text(data))
