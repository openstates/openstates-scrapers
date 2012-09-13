import os

from os.path import abspath, dirname, join

SCRAPER_PATHS=[os.path.join(os.getcwd(), 'openstates')]
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_DATABASE = 'fiftystates'

PARTY_DETAILS = {
    # Singular, Plural, Adjective
    # Democrat, Democrats, Democratic
    'Democratic': {'noun': 'Democrat', 'abbreviation': 'D'},
    # Republican, Republicans, Republican
    'Republican': {'abbreviation': 'R'},
    # Independent, Independents, Independent
    'Independent': {'abbreviation': 'I'},
    # Democratic-Farmer-Labor, DFLers, Democratic-Farmer-Labor
    'Democratic-Farmer-Labor': {'abbreviation': 'DFL',
                                'plural_noun': 'DFLers'},   # MN
    'Nonpartisan': {'abbreviation': 'NP', 'plural_noun': 'Nonpartisan'},  # NE
    'Unknown': {'abbreviation': '?', 'plural_noun': 'Unknown'},       # NY & PR
    'Partido Nuevo Progresista': {'abbreviation': 'PNP'},       # PR
    u'Partido Popular Democr\xe1tico': {'abbreviation': 'PPD'}, # PR
    'Carter County Republican': {'abbreviation': 'CCR'},    # TN
    'Working Families': {'abbreviation': 'WF'},             # NY & VT
    'Conservative': {'abbreviation': 'C'},                  # NY
    'Progressive': {'abbreviation': 'P'},                   # VT
}


try:
    from billy_local import *
except ImportError:
    pass
