import os

from os.path import abspath, dirname, join

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# This shims around folks that have openstates/ on virtualenv's .pth, but
# not the root. This throws openstates.utils off, and isn't worth fiddling
# that much with.

SCRAPER_PATHS=[os.path.join(os.getcwd(), 'openstates')]
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_DATABASE = 'fiftystates'

BILLY_MANUAL_DATA_DIR = os.environ.get('BILLY_MANUAL_DATA_DIR')
if BILLY_MANUAL_DATA_DIR is None:
    BILLY_MANUAL_DATA_DIR = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        "manual_data",
    )

LEGISLATOR_FILTERS = {
    "billy.importers.filters.single_space_filter": [
        "full_name",
        "first_name",
        "last_name",
        "middle_name",
    ],
    "billy.importers.filters.phone_filter": [
        "office_phone",
        "phone",
        "offices.phone",
        "offices.fax",
    ],
    "billy.importers.filters.email_filter": [
        "offices.email",
    ],
}

BILL_FILTERS = {
    "billy.importers.filters.single_space_filter": [
        "actions.action",
        "title",
    ]
}

EVENT_FILTERS = {
    "billy.importers.filters.single_space_filter": [
        "description",
        "participants.participant",
        "related_bills.bill_id",
        "related_bills.description",
    ]
}


try:
    from billy_local import *
except ImportError:
    pass
