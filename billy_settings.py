import os

from os.path import abspath, dirname, join

SCRAPER_PATHS=[os.path.join(os.getcwd(), 'openstates')]
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_DATABASE = 'fiftystates'

PARTY_DETAILS = {
    # reminder: think through Singular, Plural, Adjective
    'Democratic': {'noun': 'Democrat', 'abbreviation': 'D'},
    'Republican': {'abbreviation': 'R'},
    'Independent': {'abbreviation': 'I'},
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
    'Republican/Democratic': {'plural_noun': 'Republican/Democratic'},   # VT
}


# LEGISLATOR_FILTERS = {
#     "billy.importers.filters.single_space_filter": [
#         "full_name",
#         "first_name",
#         "last_name",
#         "middle_name",
#     ],
#     "billy.importers.filters.phone_filter": [
#         "office_phone",
#         "phone",
#         "offices.phone",
#         "offices.fax",
#     ],
#     "billy.importers.filters.email_filter": [
#         "offices.email",
#     ],
# }
# 
# BILL_FILTERS = {
#     "billy.importers.filters.single_space_filter": [
#         "actions.action",
#         "title",
#     ]
# }
# 
# EVENT_FILTERS = {
#     "billy.importers.filters.single_space_filter": [
#         "description",
#         "participants.participant",
#         "related_bills.bill_id",
#         "related_bills.description",
#     ]
# }


BOUNDARY_SERVICE_SETS = 'sldl,sldu'
ENABLE_DOCUMENT_VIEW = {
    'ak': True,
    'al': True,
    'ar': False,    # revisit
    'az': True,
    'ca': False,
    'co': False,    # revisit
    'ct': True,
    'dc': True,
    'de': True,
    'fl': True,
    'ga': False,
    'hi': True,
    'ia': True,
    'id': True,
    'il': True,
    'in': True,
    'ks': True,
    'ky': True,
    'la': False,    # revisit
    'ma': False,
    'md': True,
    'me': True,
    'mi': True,
    'mn': False,
    'mo': True,
    'ms': True,
    'mt': True,
    'nc': True,
    'nd': True,
    'ne': True,
    'nh': True,
    'nj': True,
    'nm': True,
    'nv': True,
    'ny': False,
    'oh': True,
    'ok': True,
    'or': True,
    'pa': False,    # revisit
    'pr': True,
    'ri': False,    # revisit
    'sc': True,
    'sd': False,
    'tn': True,
    'tx': False,    # revisit
    'ut': True,
    'va': False,
    'vt': True,
    'wa': False,    # revisit
    'wi': True,
    'wv': False,
    'wv': True
}

try:
    from billy_local import *
except ImportError:
    pass
