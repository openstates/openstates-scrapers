import lxml.html
import datetime
from .legislators import TXLegislatorScraper
from .committees import TXCommitteeScraper
from .bills import TXBillScraper
from .votes import TXVoteScraper
from .events import TXEventScraper

metadata = dict(
    name='Texas',
    abbreviation='tx',
    legislature_name='Texas Legislature',
    legislature_url='http://www.capitol.state.tx.us/',
    capitol_timezone='America/Chicago',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '81',
         'sessions': ['81', '811'],
         'start_year': 2009, 'end_year': 2010,
         'type': 'primary'},
        {'name': '82',
         'sessions': ['82', '821'],
         'start_year': 2011, 'end_year': 2012,},
        {'name': '83',
         'sessions': ['83', '831', '832', '833'],
         'start_year': 2013, 'end_year': 2014,},
        {'name': '84',
         'sessions': ['84'],
         'start_year': 2015, 'end_year': 2015,},
        ],
    session_details={
        '81': {'start_date': datetime.date(2009, 1, 13),
               'end_date': datetime.date(2009, 6, 1),
               'type': 'primary',
               'display_name': '81st Legislature (2009)',
                '_scraped_name': '81(R) - 2009',
              },
        '811': {'start_date': datetime.date(2009, 7, 1),
                'end_date': datetime.date(2009, 7, 10),
                'type': 'special',
                'display_name': '81st Legislature, 1st Called Session (2009)',
                '_scraped_name': '81(1) - 2009',
               },
        '82': {'start_date': datetime.date(2011, 1, 11),
               'type': 'primary',
               'display_name': '82nd Legislature (2011)',
               '_scraped_name': '82(R) - 2011',
              },
        '821': {'type': 'special',
                'display_name': '82nd Legislature, 1st Called Session (2011)',
                '_scraped_name': '82(1) - 2011',
               },
        '83': {'start_year': 2013,
               'end_year': 2014,
               'type': 'primary',
               'display_name': '83rd Legislature (2013)',
               '_scraped_name': '83(R) - 2013',
              },
        '831': {'type': 'special',
                'display_name': '83nd Legislature, 1st Called Session (2013)',
                '_scraped_name': '83(1) - 2013',
               },
        '832': {'type': 'special',
                'display_name': '83nd Legislature, 2st Called Session (2013)',
                '_scraped_name': '83(2) - 2013',
               },
        '833': {'type': 'special',
                'display_name': '83nd Legislature, 3rd Called Session (2013)',
                '_scraped_name': '83(3) - 2013',
               },
        '84': {'start_year': 2015,
               'end_year': 2015,
               'type': 'primary',
               'display_name': '84th Legislature (2015)',
               '_scraped_name': '84(R) - 2015',
              },
    },
    feature_flags=['events', 'subjects', 'capitol_maps', 'influenceexplorer'],
    capitol_maps=[
        {"name": "Capitol Complex",
     "url": 'http://static.openstates.org/capmaps/tx/Map.CapitolComplex.pdf'
        },
        {"name": "Floor 1",
         "url": 'http://static.openstates.org/capmaps/tx/Map.Floor1.pdf'
        },
        {"name": "Floor 2",
         "url": 'http://static.openstates.org/capmaps/tx/Map.Floor2.pdf'
        },
        {"name": "Floor 3",
         "url": 'http://static.openstates.org/capmaps/tx/Map.Floor3.pdf'
        },
        {"name": "Floor 4",
         "url": 'http://static.openstates.org/capmaps/tx/Map.Floor4.pdf'
        },
        {"name": "Floor E1",
         "url": 'http://static.openstates.org/capmaps/tx/Map.FloorE1.pdf'
        },
        {"name": "Floor E2",
         "url": 'http://static.openstates.org/capmaps/tx/Map.FloorE2.pdf'
        },
        {"name": "Floor G",
         "url": 'http://static.openstates.org/capmaps/tx/Map.FloorG.pdf'
        },
        {"name": "Monument Guide",
         "url": 'http://static.openstates.org/capmaps/tx/Map.MonumentGuide.pdf'
        },
        {"name": "Sam Houston",
         "url": 'http://static.openstates.org/capmaps/tx/Map.SamHoustonLoc.pdf'
        },
        {"name": "Wheelchair Access",
     "url": 'http://static.openstates.org/capmaps/tx/Map.WheelchairAccess.pdf'
        },
    ],
    _ignored_scraped_sessions=['80(R) - 2007', '79(3) - 2006', '79(2) - 2005',
                               '79(1) - 2005', '79(R) - 2005', '78(4) - 2004',
                               '78(3) - 2003', '78(2) - 2003', '78(1) - 2003',
                               '78(R) - 2003', '77(R) - 2001', '76(R) - 1999',
                               '75(R) - 1997', '74(R) - 1995', '73(R) - 1993',
                               '72(4) - 1992', '72(3) - 1992', '72(2) - 1991',
                               '72(1) - 1991', '72(R) - 1991', '71(6) - 1990',
                               '71(5) - 1990', '71(4) - 1990', '71(3) - 1990',
                               '71(2) - 1989', '71(1) - 1989', '71(R) - 1989']

)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath( 'http://www.legis.state.tx.us/',
        "//select[@name='cboLegSess']/option/text()")


def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    return doc.xpath('//html')[0].text_content()
