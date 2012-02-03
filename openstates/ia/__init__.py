import datetime

metadata = dict(
    name='Iowa',
    abbreviation='ia',
    legislature_name='Iowa General Assembly',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
        {
            'name': '2011-2012',
            'start_year': 2011,
            'end_year': 2012,
            'sessions': ['2011-2012'],
        },
    ],
    session_details={
        '2011-2012': {'display_name': '2011-2012 Regular Session',
                      '_scraped_name': 'General Assembly: 84',
                      'number': '84',
                      'start_date': datetime.date(2011,1,10),
                      'end_date': datetime.date(2013,1,13),
                     },
    },
    feature_flags=[],
    _ignored_scraped_sessions=['General Assembly: 83', 'General Assembly: 82',
                               'General Assembly: 81', 'General Assembly: 80']

)

def session_list():
    from billy.scrape.utils import url_xpath
    import re
    sessions = url_xpath(
        'https://www.legis.iowa.gov/Legislation/Find/findLegislation.aspx',
        "//div[@id='ctl00_ctl00_ctl00_cphMainContent_cphCenterCol_cphCenterCol_ucGASelect_divLinks']/ul/li/a/text()" )
    sessions = [
        re.findall(".*\(", session)[0][:-1].strip()
        for session in sessions
    ]
    return sessions
