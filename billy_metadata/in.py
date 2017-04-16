import datetime
import lxml.html


metadata = dict(
    name='Indiana',
    abbreviation='in',
    capitol_timezone='America/Indiana/Indianapolis',
    legislature_name='Indiana General Assembly',
    legislature_url='http://www.in.gov/legislative/',
    chambers={
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2009-2010', 'start_year': 2009,
         'end_year': 2010, 'sessions': ['2009', '2010']},
        {'name': '2011-2012', 'start_year': 2011,
         'end_year': 2012, 'sessions': ['2011', '2012']},
        {'name': '2013-2014', 'start_year': 2013,
         'end_year': 2014, 'sessions': ['2013', '2014']},
        {'name': '2015-2016', 'start_year': 2015,
         'end_year': 2016, 'sessions': ['2015', '2016']},
        {'name': '2017-2017', 'start_year': 2017,
         'end_year': 2018, 'sessions': ['2017']},
    ],
    session_details={
        '2009': {'display_name': '2009 Regular Session',
            '_scraped_name': 'First Regular Session 116th General Assembly (2009)'},
        '2010': {'display_name': '2010 Regular Session',
            '_scraped_name': 'Second Regular Session 116th General Assembly (2010)'},
        '2011': {'start_date': datetime.date(2011, 1, 5),
            'display_name': '2011 Regular Session',
            '_scraped_name': 'First Regular Session 117th General Assembly (2011)'},
        '2012': {'display_name': '2012 Regular Session',
            '_scraped_name': 'Second Regular Session 117th General Assembly (2012)'},
        '2013': {'display_name': '2013 Regular Session',
            '_scraped_name': 'First Regular Session 118th General Assembly (2013)'},
        '2014': {'display_name': '2014 Regular Session',
            '_scraped_name': 'Second Regular Session 118th General Assembly (2014)'},
        '2015': {'display_name': '2015 Regular Session',
            '_scraped_name': 'First Regular Session 119th General Assembly (2015)'},
        '2016': {'display_name': '2016 Regular Session',
            '_scraped_name': 'Second Regular Session 119th General Assembly (2016)'},
        '2017': {'display_name': '2017 Regular Session',
            '_scraped_name': 'First Regular Session 120th General Assembly (2017)',
            'start_date': datetime.date(2017, 1, 9),
            'end_date': datetime.date(2017, 4, 29)},
    },
    feature_flags=['subjects', 'capitol_maps', 'influenceexplorer'],
    capitol_maps=[
        {"name": "Floor 1",
         "url": 'http://static.openstates.org/capmaps/in/floor1.gif'
         },
        {"name": "Floor 2",
         "url": 'http://static.openstates.org/capmaps/in/floor2.gif'
         },
        {"name": "Floor 3",
         "url": 'http://static.openstates.org/capmaps/in/floor3.gif'
         },
        {"name": "Floor 4",
         "url": 'http://static.openstates.org/capmaps/in/floor4.gif'
         },
    ],
    _ignored_scraped_sessions=[
        '2012 Regular Session',
        '2011 Regular Session',
        '2010 Regular Session',
        '2009 Special Session',
        '2009 Regular Session',
        '2008 Regular Session',
        '2007 Regular Session',
        '2006 Regular Session',
        '2005 Regular Session',
        '2004 Regular Session',
        '2003 Regular Session',
        '2002 Special Session',
        '2002 Regular Session',
        '2001 Regular Session',
        '2000 Regular Session',
        '1999 Regular Session',
        '1998 Regular Session',
        '1997 Regular Session']
)

def session_list():
    import requests
    import os
    apikey = os.environ['INDIANA_API_KEY']
    headers = {"Authorization": apikey,
               "Accept": "application/json"}
    resp = requests.get("https://api.iga.in.gov/sessions", headers=headers, verify=False)
    resp.raise_for_status()
    return [session["name"] for session in resp.json()["items"]]

