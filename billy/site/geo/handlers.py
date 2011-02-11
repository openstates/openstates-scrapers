from billy.site.api.handlers import FiftyStateHandler
from billy.site.geo.models import District
from billy import db

from piston.utils import rc

class LegislatorGeoHandler(FiftyStateHandler):
    def read(self, request):
        try:
            districts = District.lat_long(request.GET['lat'],
                                          request.GET['long'])

            filters = []
            for d in districts:
                filters.append({'state': d.state_abbrev,
                                'roles': {'$elemMatch': {
                                    'district': d.name,
                                    'chamber': d.chamber}}})

            if not filters:
                return []

            return list(db.legislators.find({'$or': filters}))
        except KeyError:
            resp = rc.BAD_REQUEST
            resp.write(": Need lat and long parameters")
            return resp

