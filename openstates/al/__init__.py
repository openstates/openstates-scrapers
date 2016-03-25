from billy.utils.fulltext import pdfdata_to_text, text_after_line_numbers
from .bills import ALBillScraper
from .legislators import ALLegislatorScraper


metadata = {
    'name': 'Alabama',
    'abbreviation': 'al',
    'legislature_name': 'Alabama Legislature',
    'legislature_url': 'http://www.legislature.state.al.us/',
    'capitol_timezone': 'America/Chicago',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    'terms': [
        {
            'name': '2011-2014',
            'start_year': 2011,
            'end_year': 2014,
            'sessions': ['2011rs', '2012rs', '2012fs', '2013rs', '2014rs'],
        },
        {
            'name': '2015-2018',
            'start_year': 2015,
            'end_year': 2018,
            'sessions': ['2015os','2015rs', '2015fs', '2015ss', '2016rs'],
        }
    ],
    'session_details': {
        '2011rs': {
            'type': 'primary',
            'display_name': '2011 Regular Session',
            'internal_id': '1058',
            '_scraped_name': 'Regular Session 2011',
        },
        '2012rs': {
            'type': 'primary',
            'display_name': '2012 Regular Session',
            'internal_id': '1059',
            '_scraped_name': 'Regular Session 2012',
        },
        '2012fs': {
            'type': 'special',
            'display_name': 'First Special Session 2012',
            'internal_id': '1060',
            '_scraped_name': 'First Special Session 2012',
        },
        '2013rs': {
            'type': 'primary',
            'display_name': '2013 Regular Session',
            'internal_id': '1061',
            '_scraped_name': 'Regular Session 2013',
        },
        '2014rs': {
            'type': 'primary',
            'display_name': '2014 Regular Session',
            'internal_id': '1062',
            '_scraped_name': 'Regular Session 2014',
        },
        '2015os': {
            'type': 'primary',
            'display_name': '2015 Organizational Session',
            'internal_id': '1063',
            '_scraped_name': 'Organizational Session 2015',
        },
        '2015rs': {
            'type': 'primary',
            'display_name': '2015 Regular Session',
            'internal_id': '1064',
            '_scraped_name': 'Regular Session 2015',
        },
        '2015fs': {
            'type': 'special',
            'display_name': 'First Special Session 2015',
            'internal_id': '1066',
            '_scraped_name': 'First Special Session 2015',
        },
        '2015ss': {
            'type': 'special',
            'display_name': 'Second Special Session 2015',
            'internal_id': '1067',
            '_scraped_name': 'Second Special Session 2015',
        },
        '2016rs': {
            'type': 'primary',
            'display_name': '2016 Regular Session',
            'internal_id': '1065',
            '_scraped_name': 'Regular Session 2016',
        },
    },
    'feature_flags': ['subjects', 'influenceexplorer'],
    '_ignored_scraped_sessions': [
        'Regular Session 1998',
        'Organizational Session 1999',
        'Regular Session 1999',
        'First Special Session 1999',
        'Organizational Session 2011',
        'Second Special Session 1999',
        'Regular Session 2000',
        'Regular Session 2001',
        'First Special Session 2001',
        'Second Special Session 2001',
        'Third Special Session 2001',
        'Fourth Special Session 2001',
        'Regular Session 2002',
        'Organizational Session 2003',
        'Regular Session 2003',
        'First Special Session 2003',
        'Second Special Session 2003',
        'Regular Session 2004',
        'First Special Session 2004',
        'Regular Session 2005',
        'First Special Session 2005',
        'Regular Session 2006',
        'Organizational Session 2007',
        'Regular Session 2007',
        'First Special Session 2007',
        'Regular Session 2008',
        'First Special Session 2008',
        'Regular Session 2009',
        'Regular Session 2010',
        'First Special Session 2009',
        'First Special Session 2010',
        'Regular Session 2016',
    ],
}


def session_list():
    import lxml.html
    import requests

    s = requests.Session()
    r = s.get('http://alisondb.legislature.state.al.us/alison/alisonlogin.aspx')
    doc = lxml.html.fromstring(r.text)
    options = doc.xpath('//option/text()')

    return options


def extract_text(doc, data):
    text = pdfdata_to_text(data)
    return text_after_line_numbers(text)
