import datetime

metadata = {
    "lower_chamber_title": "Representative",
    "lower_chamber_name": "House of Representatives",
    "upper_chamber_title": "Senator",
    "terms": [
        {
            "name": "2008-2011",
            "start_year": 2008,
            "end_year": 2011,
            "sessions": [
                "2009",
                "2010",
                "2011 1st Extraordinary Session",
                "2011"
                ]
        },
    ],
    "name": "Louisiana",
    "upper_chamber_term": 4,
    "abbreviation": "la",
    "upper_chamber_name": "Senate",
    "session_details": {
        "2009": {
            "type": "primary",
            "start_date": datetime.date(2010, 4, 27),
            "end_date": datetime.date(2010, 6, 24),
            'display_name': '2009 Regular Session',
            '_scraped_name': '2009 Regular Legislative Session'
        },
        "2010": {
            "type": "primary",
            "start_date": datetime.date(2010, 3, 29),
            "end_date": datetime.date(2010, 6, 21),
            'display_name': '2010 Regular Session',
            '_scraped_name': '2010 Regular Legislative Session',
        },
        "2011 1st Extraordinary Session": {
            "type": "special",
            "_id": "111es",
            'display_name': '2011, 1st Extraordinary Session',
            '_scraped_name': '2011 1st Extraordinary Session',
        },
        "2011": {
            "type": "special",
            'display_name': '2011 Regular Session',
            '_scraped_name': '2011 Regular Legislative Session',
        },
    },
    "legislature_name": "Louisiana Legislature",
    "lower_chamber_term": 4,
    'feature_flags': ['subjects'],
    '_ignored_scraped_sessions': [
        '2008 Regular Legislative Session',
        '2008 2nd Extraordinary Session',
        '2008 1st Extraordinary Session',
        '2008 Organizational Session',
        '2007 Regular Legislative Session',
        '2006 2nd Extraordinary Session',
        '2006 Regular Legislative Session',
        '2006 1st Extraordinary Session',
        '2005 1st Extraordinary Session',
        '2005 Regular Legislative Session',
        '2004 Regular Legislative Session',
        '2004 1st Extraordinary Session',
        '2004 Organizational Session',
        '2003 Regular Legislative Session',
        '2002 Regular Legislative Session',
        '2002 1st Extraordinary Session',
        '2001 2nd Extraordinary Session',
        '2001 Regular Legislative Session',
        '2001 1st Extraordinary Session',
        '2000 2nd Extraordinary Session',
        '2000 Regular Legislative Session',
        '2000 1st Extraordinary Session',
        '2000 Organizational Session',
        '1999 Regular Legislative Session',
        '1998 Regular Legislative Session',
        '1998 1st Extraordinary Session',
        '1997 Regular Legislative Session']
}


def session_list():
    from billy.scrape.utils import url_xpath
    import re
    return [re.sub('\s+', ' ', x.text_content()) for x in
            url_xpath('http://www.legis.state.la.us/session.htm', '//strong')][:-1]
