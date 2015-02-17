import datetime
from billy.utils.fulltext import pdfdata_to_text, text_after_line_numbers
from .bills import ALBillScraper
from .legislators import ALLegislatorScraper

metadata =  {
    'name': 'Alabama',
    'capitol_timezone': 'America/Chicago',
    'abbreviation': 'al',
    'legislature_name': 'Alabama Legislature',
    'legislature_url': 'http://www.legislature.state.al.us/',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    'terms': [
        #{'name': '2007-2010',
        # 'sessions': ['Organization Session 2007',
        #              'Regular Session 2007',
        #              'Regular Session 2008',
        #              'First Special Session 2008',
        #              'Regular Session 2009',
        #              'First Special Session 2009',
        #              'Regular Session 2010'],
        # 'start_year': 2009,
        # 'end_year': 2010},
        {'name': '2011-2014',
         'sessions': ['2011rs','2012rs', 'First Special Session 2012',
                      '2013rs', '2014rs'],
         'start_year': 2011,
         'end_year': 2014,
        },
        {'name': '2015-2018',
         'sessions': ['2015os','2015rs'],
         'start_year': 2015,
         'end_year': 2018,
        }
    ],
    'feature_flags': ['subjects', 'influenceexplorer'],
    'session_details':{
        #'Organization Session 2007': {
        #    'start_date': datetime.date(2007, 1, 9),
        #    'end_date': datetime.date(2007, 1, 16),
        #    'type': 'special',
        #    'internal_id': 1034,
        #},
        #'Regular Session 2007': {
        #    'start_date': datetime.date(2007, 3, 6),
        #    'end_date': datetime.date(2007, 6, 7),
        #    'type': 'primary',
        #    'internal_id': 1036,
        #},
        #'Regular Session 2008': {
        #    'start_date': datetime.date(2008, 2, 5),
        #    'end_date': datetime.date(2008, 5, 19),
        #    'type': 'primary',
        #    'internal_id': 1047,
        #},
        #'First Special Session 2008': {
        #    'start_date': datetime.date(2008, 5, 31),
        #    'end_date': datetime.date(2008, 5, 27),
        #    'type': 'special',
        #    'internal_id': 1048,
        #},
        #'Regular Session 2009': {
        #    'start_date': datetime.date(2009, 2, 3),
        #    'end_date': datetime.date(2009, 5, 15),
        #    'type': 'primary',
        #    'internal_id': 1049,
        #},
        #'First Special Session 2009': {
        #    'start_date': datetime.date(2009, 8, 14),
        #    'end_date': datetime.date(2009, 8, 10),
        #    'type': 'special',
        #    'internal_id': 1052,
        #},
        #'Regular Session 2010': {
        #    'start_date': datetime.date(2010, 1, 12),
        #    'end_date': datetime.date(2010, 4, 22),
        #    'type': 'primary',
        #    'internal_id': 1051,
        #},
        '2011rs': {
            'display_name': '2011 Regular Session',
            'internal_id': '1058',
            'type': 'primary',
            '_scraped_name': 'Regular Session 2011',
        },
        '2012rs': {
            'display_name': '2012 Regular Session',
            'internal_id': '1059',
            'type': 'primary',
            '_scraped_name': 'Regular Session 2012',
        },
        'First Special Session 2012': {
            'display_name': 'First Special Session 2012',
            'internal_id': '1060',
            'type': 'special',
            '_scraped_name': 'First Special Session 2012',
        },
        '2013rs': {
            'display_name': '2013 Regular Session',
            'internal_id': '1061',
            'type': 'primary',
            '_scraped_name': 'Regular Session 2013',
        },
        '2014rs': {
            'display_name': '2014 Regular Session',
            'internal_id': '1062',
            'type': 'primary',
            '_scraped_name': 'Regular Session 2014',
        },
        '2015os': {
            'display_name': '2015 Organizational Session',
            'internal_id': '1063',
            'type': 'primary',
            '_scraped_name': 'Organizational Session 2015',
        },
        '2015rs': {
            'display_name': '2015 Regular Session',
            'internal_id': '1064',
            'type': 'primary',
            '_scraped_name': 'Regular Session 2015',
        },
    },
    '_ignored_scraped_sessions': [
        'First Special Session 2010',
        'First Special Session 2009',
        'Regular Session 2010',
        'Regular Session 2009',
        'First Special Session 2008',
        'Regular Session 2008',
        'First Special Session 2007',
        'Regular Session 2007',
        'Organizational Session 2007',
        'Regular Session 2006',
        'First Special Session 2005',
        'Regular Session 2005',
        'First Special Session 2004',
        'Regular Session 2004',
        'Second Special Session 2003',
        'First Special Session 2003',
        'Regular Session 2003',
        'Organizational Session 2003',
        'Regular Session 2002',
        'Fourth Special Session 2001',
        'Third Special Session 2001',
        'Second Special Session 2001',
        'First Special Session 2001',
        'Regular Session 2001',
        'Regular Session 2000',
        'Organizational Session 2011']
}


def session_list():
    from billy.scrape.utils import url_xpath
    sessions = url_xpath('http://alisondb.legislature.state.al.us/acas/ACTIONSessionResultsMac.asp',
        '//option/text()' )
    return [s.strip() for s in sessions]


def extract_text(doc, data):
    text = pdfdata_to_text(data)
    return text_after_line_numbers(text)
