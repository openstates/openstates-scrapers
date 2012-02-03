metadata = {
    'name': 'Montana',
    'abbreviation': 'mt',
    'legislature_name': 'Montana Legislature',
    'upper_chamber_name': 'Senate',
    'lower_chamber_name': 'House of Representatives',
    'upper_chamber_title': 'Senator',
    'lower_chamber_title': 'Representative',
    'upper_chamber_term': 4,
    'lower_chamber_term': 2,
    'terms': [
        {'name': '62nd',
         'sessions': ['62nd'],
         'start_year': 2011, 'end_year': 2012},
    ],
    'session_details': {
        '62nd': {'display_name': '62nd Regular Session',
                 'years': [2011, 2012]
                },
    },
    'feature_flags': [],
}

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://leg.mt.gov/css/bills/Default.asp',
        "//td[@id='cont']/ul/li/a/text()")

