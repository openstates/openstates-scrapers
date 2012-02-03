metadata = dict(
    name='Florida',
    abbreviation='fl',
    legislature_name='Florida Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
        {'name': '2011-2012',
         'sessions': ['2011', '2012'],
         'start_year': 2011, 'end_year': 2012}],
    session_details={
        '2011': {'display_name': '2011 Regular Session',
                 '_scraped_name': '2011',
                },
        '2012': {'display_name': '2012 Regular Session',
                 '_scraped_name': '2012',
                },
    },
    feature_flags=[],
    _ignored_scraped_sessions=['2010O', '2010A'],
)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://flsenate.gov', '//option/text()')


