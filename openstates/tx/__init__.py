import datetime

metadata = dict(
    name='Texas',
    abbreviation='tx',
    legislature_name='Texas Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
        {'name': '81',
         'sessions': ['81', '811'],
         'start_year': 2009, 'end_year': 2010,
         'type': 'primary'},
        {'name': '82',
         'sessions': ['82', '821'],
         'start_year': 2011, 'end_year': 2012,},
        ],
    session_details={
        '81': {'start_date': datetime.date(2009, 1, 13),
               'end_date': datetime.date(2009, 6, 1),
               'type': 'primary',
               'display_name': '81st Legislature',
                '_scraped_name': '81(R) - 2009',
              },
        '811': {'start_date': datetime.date(2009, 7, 1),
                'end_date': datetime.date(2009, 7, 10),
                'type': 'special',
                'display_name': '81st Legislature, 1st Called Session',
                '_scraped_name': '81(1) - 2009',
               },
        '82': {'start_date': datetime.date(2011, 1, 11),
               'type': 'primary',
               'display_name': '82nd Legislature',
               '_scraped_name': '82(R) - 2011',
              },
        '821': {'type': 'special',
                'display_name': '82nd Legislature, 1st Called Session',
                '_scraped_name': '82(1) - 2011',
               }
    },
    feature_flags=['events', 'subjects', 'capitol_maps'],
    capitol_maps=[
        {"name": "Capitol Complex",
         "url": 'https://s3.amazonaws.com/assets.openstates.org/capmaps/tx/Map.CapitolComplex.pdf'
        },
        {"name": "Floor 1",
         "url": 'https://s3.amazonaws.com/assets.openstates.org/capmaps/tx/Map.Floor1.pdf'
        },
        {"name": "Floor 2",
         "url": 'https://s3.amazonaws.com/assets.openstates.org/capmaps/tx/Map.Floor2.pdf'
        },
        {"name": "Floor 3",
         "url": 'https://s3.amazonaws.com/assets.openstates.org/capmaps/tx/Map.Floor3.pdf'
        },
        {"name": "Floor 4",
         "url": 'https://s3.amazonaws.com/assets.openstates.org/capmaps/tx/Map.Floor4.pdf'
        },
        {"name": "Floor E1",
         "url": 'https://s3.amazonaws.com/assets.openstates.org/capmaps/tx/Map.FloorE1.pdf'
        },
        {"name": "Floor E2",
         "url": 'https://s3.amazonaws.com/assets.openstates.org/capmaps/tx/Map.FloorE2.pdf'
        },
        {"name": "Floor G",
         "url": 'https://s3.amazonaws.com/assets.openstates.org/capmaps/tx/Map.FloorG.pdf'
        },
        {"name": "Monument Guide",
         "url": 'https://s3.amazonaws.com/assets.openstates.org/capmaps/tx/Map.MonumentGuide.pdf'
        },
        {"name": "Sam Houston",
         "url": 'https://s3.amazonaws.com/assets.openstates.org/capmaps/tx/Map.SamHoustonLoc.pdf'
        },
        {"name": "Wheelchair Access",
         "url": 'https://s3.amazonaws.com/assets.openstates.org/capmaps/tx/Map.WheelchairAccess.pdf'
        },
    ],
    _ignored_scraped_sessions=['80(R) - 2007', '79(3) - 2006', '79(2) - 2005',
                               '79(1) - 2005', '79(R) - 2005', '78(4) - 2004',
                               '78(3) - 2003', '78(2) - 2003', '78(1) - 2003',
                               '78(R) - 2003', '77(R) - 2001', '76(R) - 1999',
                               '75(R) - 1997', '74(R) - 1995', '73(R) - 1993',
                               '72(4) - 1992', '72(3) - 1992', '72(2) - 1991',
                               '72(1) - 1991', '72(R) - 1991', '71(6) - 1990',
                               '71(5) - 1990', '71(4) - 1990', '71(3) - 1990',
                               '71(2) - 1989', '71(1) - 1989', '71(R) - 1989']

)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath( 'http://www.legis.state.tx.us/',
        "//select[@name='cboLegSess']/option/text()")
