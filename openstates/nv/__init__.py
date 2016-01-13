import datetime
from billy.scrape.utils import url_xpath
from billy.utils.fulltext import pdfdata_to_text, text_after_line_numbers
from .bills import NVBillScraper
from .legislators import NVLegislatorScraper
from .committees import NVCommitteeScraper

metadata = {
    'name': 'Nevada',
    'abbreviation': 'nv',
    'legislature_name': 'Nevada Legislature',
    'legislature_url': 'http://www.leg.state.nv.us/',
    'capitol_timezone': 'America/Los_Angeles',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'Assembly', 'title': 'Assembly Member'},
    },
    'terms': [
        #{'name': '2001-2002', 'start_year': 2001, 'end_year': 2002,
        # 'sessions': ['2001Special17', '2002Special18', '71'],
        #},
        #{'name': '2003-2004', 'start_year': 2003, 'end_year': 2004,
        # 'sessions': ['2003Special19', '2003Special20', '2004Special21', '72']
        #},
        #{'name': '2005-2006', 'start_year': 2005, 'end_year': 2006,
        # 'sessions': ['2005Special22', '73']
        #},
        #{'name': '2007-2008', 'start_year': 2007, 'end_year': 2008,
        # 'sessions': ['2007Special23', '2008Special24', '2008Special25', '74']
        #},
        {
            'name': '2009-2010',
            'start_year': 2009,
            'end_year': 2010,
            'sessions': ['2010Special26', '75'],
        },
        {
            'name': '2011-2012',
            'start_year': 2011,
            'end_year': 2012,
            'sessions': ['76'],
        },
        {
            'name': '2013-2014',
            'start_year': 2013,
            'end_year': 2014,
            'sessions': ['77', '2013Special27', '2014Special28'],
        },
        {
            'name': '2015-2016',
            'start_year': 2015,
            'end_year': 2016,
            'sessions': ['78', '2015Special29'],
        },
    ],
    'session_details': {
        '2010Special26': {
            'type':'special',
            'display_name': '26th Special Session (2010)',
            '_scraped_name': '26th (2010) Special Session',
            'slug': '26th2010Special',
        },
        '75': {
            'type': 'primary',
            'display_name': '2009 Regular Session',
            '_scraped_name': '75th (2009) Session',
            'slug': '75th2009',
        },
        '76': {
            'type': 'primary',
            'display_name': '2011 Regular Session',
            '_scraped_name': '76th (2011) Session',
            'slug': '76th2011',
        },
        '77': {
            'type': 'primary',
            'display_name': '2013 Regular Session',
            '_scraped_name': u'77th (2013) Session\xa0\xa0(click to close)',
            'slug': '77th2013',
        },
        '2013Special27': {
            'type': 'special',
            'display_name': '27th Special Session (2013)',
            '_scraped_name': u'27th (2013) Special Session\xa0\xa0(click to close)',
            '_committee_session': '77th2013',
            'slug': '27th2013Special',
        },
        '2014Special28': {
            'type': 'special',
            'display_name': '28th Special Session (2014)',
            '_scraped_name': u'28th (2014) Special Session\xa0\xa0(click to close)',
            '_committee_session': '28th2014Special',
            'slug': '28th2014Special',
        },
	'78': {
            'type': 'primary',
            'start_date': datetime.date(2015, 2, 15),
            'end_date': datetime.date(2015, 6, 1),
            'display_name': '2015 Regular Session',
            '_scraped_name': u'78th (2015) Session\xa0\xa0(click to close)',
            'slug': '78th2015',
        },
        '2015Special29': {
            'type': 'special',
            'start_date': datetime.date(2015, 12, 16),
            'end_date': datetime.date(2015, 12, 19),
            'display_name': '29th Special Session (2015)',
            '_scraped_name': u'29th (2015) Special Session\xa0\xa0(click to close)',
            '_committee_session': '29th2015Special',
            'slug': '29th2015Special',
        },
    },
    'feature_flags': ['subjects', 'capitol_maps', 'influenceexplorer'],
    'capitol_maps': [
        {
            "name": "Floor 1",
            "url": 'http://static.openstates.org/capmaps/nv/Leg1.gif'
        },
        {
            "name": "Floor 2",
            "url": 'http://static.openstates.org/capmaps/nv/Leg2.gif'
        },
        {
            "name": "Floor 3",
            "url": 'http://static.openstates.org/capmaps/nv/Leg3.gif'
        },
        {
            "name": "Floor 4",
            "url": 'http://static.openstates.org/capmaps/nv/Leg4.gif'
        },
    ],
    '_ignored_scraped_sessions': [
        '25th (2008) Special Session',
        '24th (2008) Special Session',
        '23rd (2007) Special Session',
        '74th (2007) Session',
        '22nd (2005) Special Session',
        '73rd (2005) Session',
        '21st (2004) Special Session',
        '20th (2003) Special Session',
        '19th (2003) Special Session',
        '72nd (2003) Session',
        '18th (2002) Special Session',
        '17th (2001) Special Session',
        '71st (2001) Session',
        '70th (1999) Session',
        '69th (1997) Session',
        '68th (1995) Session',
        '67th (1993) Session',
        '66th (1991) Session',
        '16th (1989) Special Session',
        '65th (1989) Session',
        '64th (1987) Session',
        '63rd (1985) Session',
    ],
}


def session_list():
    return [x.text_content() for x in
            url_xpath('http://www.leg.state.nv.us/Session/',
                      '//*[@class="MainHeading"]')]


def extract_text(doc, data):
    return text_after_line_numbers(pdfdata_to_text(data))
