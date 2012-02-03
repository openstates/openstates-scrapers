metadata = {
    'name': 'Michigan',
    'abbreviation': 'mi',
    'legislature_name': 'Michigan Legislature',
    'lower_chamber_name': 'House of Representatives',
    'upper_chamber_name': 'Senate',
    'lower_chamber_title': 'Representative',
    'upper_chamber_title': 'Senator',
    'lower_chamber_term': 2,
    'upper_chamber_term': 4,
    'terms': [
        {'name': '2011-2012', 'sessions': ['2011-2012'],
         'start_year': 2011, 'end_year': 2012},
    ],
    'session_details': {
        '2011-2012': {'type':'primary',
                      'display_name': '2011-2012 Regular Session',
                      '_scraped_name': '2011-2012',
                     },
    },
    'feature_flags': ['subjects'],
    '_ignored_scraped_sessions': ['2009-2010', '2007-2008', '2005-2006',
                                  '2003-2004', '2001-2002', '1999-2000',
                                  '1997-1998', '1995-1996']

}


def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.legislature.mi.gov/mileg.aspx?'
                     'page=LegBasicSearch', '//option/text()')
