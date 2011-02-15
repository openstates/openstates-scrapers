import json
import urllib2

from billy.site.api.handlers import FiftyStateHandler
from billy.site.geo.models import District
from billy import db

from piston.utils import rc


class LegislatorGeoHandler(FiftyStateHandler):
    def read(self, request):
        try:
            latitude, longitude = request.GET['lat'], request.GET['long']
        except KeyError:
            resp = rc.BAD_REQUEST
            resp.write(': Need lat and long parameters')
            return resp

        url = "http://localhost:8001/1.0/boundary/?contains=%s,%s&sets=sldl,sldu" % (latitude, longitude)

        resp = json.load(urllib2.urlopen(url))

        filters = []
        ret = []
        for dist in resp['objects']:
            state = dist['name'][0:2].lower()
            name = dist['name'].split('District ')[1]
            chamber = {'/1.0/boundary-set/sldu/': 'upper',
                       '/1.0/boundary-set/sldl/': 'lower'}[dist['set']]


            filters.append({'state': state, 'district': name,
                            'chamber': chamber})

        if not filters:
            return []

        return list(db.legislators.find({'$or': filters}))
