from billy.core import db
from billy_settings import LEGISLATOR_FILTERS
from billy.importers.filters import apply_filters
from dictdiffer import diff


filters = LEGISLATOR_FILTERS


for leg in db.legislators.find():
    d1 = leg
    leg = leg.copy()
    d2 = apply_filters(filters, leg)
    changes = list(diff(d1, d2))
    if changes != []:
        print leg['_id'], changes
