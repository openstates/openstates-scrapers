import datetime
from billy.utils.fulltext import (pdfdata_to_text, oyster_text,
                            text_after_line_numbers)

metadata = dict(
    name = 'North Dakota',
    abbreviation = 'nd',
    legislature_name = 'North Dakota Legislative Assembly',
    capitol_timezone='America/Chicago',
    upper_chamber_name = 'Senate',
    lower_chamber_name  = 'House',
    upper_chamber_title = 'Senator',
    lower_chamber_title = 'Representative',
    upper_chamber_term = 4,
    lower_chamber_term = 4,
    terms = [
        {'name': '62', 'sessions': ['62'],
         'start_year': 2011, 'end_year': 2012},
        # 2013 term is already there, but we avoid scraping it
        #{'name': '63', 'sessions': ['63'],
        # 'start_year': 2013, 'end_year': 2014},
    ],
    session_details={
        '62' : {'start_date' : datetime.date(2011, 1, 4),
                'display_name' : '62nd Legislative Assembly',
                '_scraped_name': '62nd (2011)',
               },
        #'63' : {'start_date': datetime.date(2013, 1, 8),
        #        'display_name' : '63rd Legislative Assembly',
        #        '_scraped_name': '63rd (2013)',
        #       }
    },
    feature_flags=['influenceexplorer'],
    _ignored_scraped_sessions=['61st (2009)', '60th (2007)', '59th (2005)',
                               '58th (2003)', '57th (2001)', '56th (1999)',
                               '55th (1997)', '54th (1995)', ]
)

def session_list():
    import scrapelib
    import lxml.html

    url = 'http://www.legis.nd.gov/assembly/'
    sessions = []

    html = scrapelib.urlopen(url)
    doc = lxml.html.fromstring(html)
    doc.make_links_absolute(url)
    # go through links and look for pages that have an active Legislation: link
    for a in doc.xpath("//div[@class='linkblockassembly']/div/span/a"):
        ahtml = scrapelib.urlopen(a.get('href'))
        adoc = lxml.html.fromstring(ahtml)
        if adoc.xpath('//a[contains(@href, "leginfo")]'):
            sessions.append(a.text)
    return sessions

@oyster_text
def extract_text(oyster_doc, data):
    return text_after_line_numbers(pdfdata_to_text(data))

document_class = dict(
    AWS_PREFIX = 'documents/nd/',
    update_mins = None,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
