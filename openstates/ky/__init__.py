from billy.utils.fulltext import worddata_to_text

metadata = dict(
    name='Kentucky',
    abbreviation='ky',
    capitol_timezone='America/New_York',
    legislature_name='Kentucky General Assembly',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        dict(
            name='2011-2012', start_year=2011, end_year=2012,
            sessions=[
                '2011 Regular Session', '2011SS', '2012RS', '2012SS'
            ]
        ),
        dict(
            name='2013-2014', start_year=2013, end_year=2014,
            sessions=[
                '2013RS',
            ]
        ),
    ],
    session_details={
        '2011 Regular Session': {'type': 'primary',
                                 'display_name': '2011 Regular Session',
                                 '_scraped_name': '2011 Regular Session',
                                },
        '2011SS': {'type': 'special',
                   'display_name': '2011 Extraordinary Session',
                   '_scraped_name': '2011 Extraordinary Session'},
        '2012RS': {'type': 'primary',
                   'display_name': '2012 Regular Session',
                   '_scraped_name': '2012 Regular Session',
                  },
        '2012SS': {'type': 'special',
                   'display_name': '2012 Extraordinary Session',
                   '_scraped_name': '2012 Extraordinary Session'},
        '2013RS': {'type': 'primary',
                   'display_name': '2013 Regular Session',
                   '_scraped_name': '2013 Regular Session',
                  },
    },
    feature_flags=['subjects', 'events', 'influenceexplorer'],
    _ignored_scraped_sessions=[],
)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.lrc.ky.gov/legislation.htm',
                     '//a[contains(@href, "record.htm")]/img/@alt')

def extract_text(doc, data):
    return worddata_to_text(data)
