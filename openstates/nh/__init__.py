metadata = {
    'abbreviation': 'nh',
    'name': 'New Hampshire',
    'legislature_name': 'New Hampshire General Court',
    'upper_chamber_name': 'Senate',
    'lower_chamber_name': 'House of Representatives',
    'upper_chamber_title': 'Senator',
    'lower_chamber_title': 'Representative',
    'upper_chamber_term': 2,
    'lower_chamber_term': 2,
    'terms': [
        {'name': '2011-2012', 'sessions': ['2011', '2012'],
         'start_year': 2011, 'end_year': 2012}
    ],
    'session_details': {
        '2011': {'display_name': '2011 Regular Session',
                 'zip_url': 'http://gencourt.state.nh.us/downloads/2011%20Session%20Bill%20Status%20Tables.zip',
                 '_scraped_name': '2011 Session',
                },
        '2012': {'display_name': '2012 Regular Session',
                 'zip_url': 'http://gencourt.state.nh.us/downloads/2012%20Session%20Bill%20Status%20Tables.zip',
                 '_scraped_name': '2012 Session',
                },
    },
    'feature_flags': [],
}

def session_list():
    from billy.scrape.utils import url_xpath
    zips = url_xpath('http://gencourt.state.nh.us/downloads/',
                     '//a[contains(@href, "Bill%20Status")]/text()')
    return [zip.replace(' Bill Status Tables.zip', '') for zip in zips]



