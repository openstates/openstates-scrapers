metadata = dict(
    name='Connecticut',
    abbreviation='ct',
    legislature_name='Connecticut General Assembly',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=2,
    lower_chamber_term=2,
    terms=[
        {'name': '2011-2012',
         'sessions': ['2011'],
         'start_year': 2011, 'end_year': 2012},
    ],
    session_details={
        '2011': {
            'display_name': '2011 Regular Session',
            '_scraped_name': '2011',
        }
    },
    feature_flags=['subjects'],
    _ignored_scraped_sessions=['2005', '2006', '2007', '2008', '2009', '2010',
                               '2012']
)

def session_list():
    import scrapelib
    text = scrapelib.urlopen('ftp://ftp.cga.ct.gov')
    sessions = [line.split()[-1] for line in text.splitlines()]
    sessions.remove('incoming')
    sessions.remove('pub')
    return sessions
