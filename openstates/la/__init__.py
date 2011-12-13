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
        },
        "2010": {
            "type": "primary",
            "start_date": datetime.date(2010, 3, 29),
            "end_date": datetime.date(2010, 6, 21),
            'display_name': '2010 Regular Session',
        },
        "2011 1st Extraordinary Session": {
            "type": "special",
            "_id": "111es",
            'display_name': '2011, 1st Extraordinary Session',
        },
        "2011": {
            "type": "special",
            'display_name': '2011 Regular Session',
        },
    },
    "legislature_name": "Louisiana Legislature",
    "lower_chamber_term": 4,
    'feature_flags': ['subjects'],
}


def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.legis.state.la.us/session.htm',
                     'string(//strong)')
