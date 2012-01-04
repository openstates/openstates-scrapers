metadata = {
    'abbreviation': 'nm',
    'name': 'New Mexico',
    'legislature_name': 'New Mexico Legislature',
    'upper_chamber_name': 'Senate',
    'lower_chamber_name': 'House of Representatives',
    'upper_chamber_title': 'Senator',
    'lower_chamber_title': 'Representative',
    'upper_chamber_term': 4,
    'lower_chamber_term': 2,
    'terms': [
        {'name': '2011-2012',
         'sessions': ['2011', '2011S'],
         'start_year': 2011, 'end_year': 2012,
        }
    ],
    'session_details': {
        '2011': {'display_name': '2011 Regular Session',
                 'slug': '11%20Regular',
                },
        '2011S': {'display_name': '2011 Special Session',
                  'slug': '11%20Special',
                 },
    },
    'feature_flags': ['subjects'],
}

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath( 'http://www.nmlegis.gov/lcs/BillFinderNumber.aspx',
        "//select[@name='ctl00$mainCopy$SessionList']/option/text()" )

