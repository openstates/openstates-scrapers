metadata = dict(
    name='Kentucky',
    abbreviation='ky',
    legislature_name='Kentucky General Assembly',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
    dict(name='2011-2012',
        start_year=2011,
        end_year=2011,
        sessions=[
            '2011 Regular Session', '2011SS',
            ])
    ],
    session_details={
        '2011 Regular Session': {'type': 'primary',
                                 'display_name': '2011 Regular Session',
                                 '_scraped_name': '2011 Regular Session',
                                },
        '2011SS': {'type': 'special',
                   'display_name': '2011 Extraordinary Session',
                   '_scraped_name': '2011 Extraordinary Session'},
    },
    feature_flags=['subjects', 'events'],
    _ignored_scraped_sessions =['2012 Regular Session',],
)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.lrc.ky.gov/legislation.htm',
                     '//a[contains(@href, "record.htm")]/img/@alt')
