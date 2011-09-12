import re
import urllib2
import datetime
import json
import itertools
from collections import defaultdict

from django.http import HttpResponse

from billy import db
from billy.conf import settings
from billy.utils import keywordize, metadata

import pymongo

from piston.utils import rc
from piston.handler import BaseHandler, HandlerMetaClass

from jellyfish import levenshtein_distance

_chamber_aliases = {
    'assembly': 'lower',
    'house': 'lower',
    'senate': 'upper',
    }


def parse_param_dt(dt):
    formats = ['%Y-%m-%d %H:%M',    # here for legacy reasons
               '%Y-%m-%dT%H:%M:%S',
               '%Y-%m-%d']
    for format in formats:
        try:
            return datetime.datetime.strptime(dt, format)
        except ValueError:
            pass


def _build_mongo_filter(request, keys, icase=True):
    # We use regex queries to get case insensitive search - this
    # means they won't use any indexes for now. Real case insensitive
    # queries are coming eventually:
    # http://jira.mongodb.org/browse/SERVER-90
    _filter = {}
    keys = set(keys) - set(['fields'])

    try:
        keys.remove('subjects')
        if 'subject' in request.GET:
            _filter['subjects'] = {'$all': request.GET.getlist('subject')}
    except KeyError:
        pass

    for key in keys:
        value = request.GET.get(key)
        if value:
            if key == 'chamber':
                value = value.lower()
                _filter[key] = _chamber_aliases.get(value, value)
            elif key.endswith('__in'):
                values = value.split('|')
                _filter[key[:-4]] = {'$in': values}
            else:
                _filter[key] = re.compile('^%s$' % value, re.IGNORECASE)

    return _filter


def _build_field_list(request, default_fields=None):
    # if 'fields' key is specified in request split it on comma
    # and use only those fields instead of default_fields
    fields = request.GET.get('fields')

    if not fields:
        return default_fields
    else:
        d = dict(zip(fields.split(','), itertools.repeat(1)))
        d['_id'] = d.pop('id', 0)
        d['_type'] = 1
        return d


class BillyHandlerMetaClass(HandlerMetaClass):
    """
    Returns 404 if Handler result is None.
    """
    def __new__(cls, name, bases, attrs):
        new_cls = super(BillyHandlerMetaClass, cls).__new__(
            cls, name, bases, attrs)

        if hasattr(new_cls, 'read'):
            old_read = new_cls.read

            def new_read(*args, **kwargs):
                request = args[1]
                fmt = request.GET.get('format')
                if fmt in ['xml', 'rss', 'ics'] and 'fields' in request.GET:
                    resp = rc.BAD_REQUEST
                    resp.write(": cannot specify fields param if format=%s" %
                               fmt)
                    return resp
                obj = old_read(*args, **kwargs)
                if isinstance(obj, HttpResponse):
                    return obj

                if obj is None:
                    return rc.NOT_FOUND

                return obj

            new_cls.read = new_read

        return new_cls


class BillyHandler(BaseHandler):
    """
    Base handler for the Billy API.
    """
    __metaclass__ = BillyHandlerMetaClass
    allowed_methods = ('GET',)


class AllMetadataHandler(BillyHandler):
    def read(self, request):
        data = db.metadata.find(fields={'level':1, 'abbreviation':1,
                                        'name':1, 'feature_flags': 1,
                                        '_id':0}).sort('name')
        return list(data)


class MetadataHandler(BillyHandler):
    def read(self, request, abbr):
        """
        Get metadata about a legislature.
        """
        return db.metadata.find_one({'_id': abbr.lower()},
                                   fields=_build_field_list(request))


class BillHandler(BillyHandler):
    def read(self, request, abbr, session, bill_id, chamber=None):
        abbr = abbr.lower()
        level = metadata(abbr)['level']
        query = {level: abbr, 'session': session, 'bill_id': bill_id}
        if chamber:
            query['chamber'] = chamber.lower()
        return db.bills.find_one(query, fields=_build_field_list(request))


class BillSearchHandler(BillyHandler):
    def read(self, request):

        bill_fields = {'title': 1, 'created_at': 1, 'updated_at': 1,
                       'bill_id': 1, 'type': 1, 'state': 1, 'level': 1,
                       'country': 1, 'session': 1, 'chamber': 1, 'subjects': 1,
                       '_type': 1}
        # replace with request's fields if they exist
        bill_fields = _build_field_list(request, bill_fields)

        # normal mongo search logic
        _filter = _build_mongo_filter(request, ('state', 'chamber',
                                                'subjects', 'bill_id',
                                                'bill_id__in'))

        # process full-text query
        query = request.GET.get('q')
        if query:
            keywords = list(keywordize(query))
            _filter['_keywords'] = {'$all': keywords}

        # process search_window
        search_window = request.GET.get('search_window', '')
        if search_window:
            if search_window == 'session':
                _filter['_current_session'] = True
            elif search_window == 'term':
                _filter['_current_term'] = True
            elif search_window.startswith('session:'):
                _filter['session'] = search_window.split('session:')[1]
            elif search_window.startswith('term:'):
                _filter['_term'] = search_window.split('term:')[1]
            elif search_window == 'all':
                pass
            else:
                resp = rc.BAD_REQUEST
                resp.write(": invalid search_window. Valid choices are "
                           "'term', 'session' or 'all'")
                return resp

        # process updated_since
        since = request.GET.get('updated_since')
        if since:
            try:
                _filter['updated_at'] = {'$gte': parse_param_dt(since)}
            except ValueError:
                resp = rc.BAD_REQUEST
                resp.write(": invalid updated_since parameter."
                           " Please supply a date in YYYY-MM-DD format.")
                return resp

        # process sponsor_id
        sponsor_id = request.GET.get('sponsor_id')
        if sponsor_id:
            _filter['sponsors.leg_id'] = sponsor_id

        query = db.bills.find(_filter, bill_fields)

        # sorting
        sort = request.GET.get('sort')
        if sort == 'updated_at':
            query = query.sort([('updated_at', -1)])

        return list(query)


class LegislatorHandler(BillyHandler):
    def read(self, request, id):
        return db.legislators.find_one({'_all_ids': id},
                                       _build_field_list(request))


class LegislatorSearchHandler(BillyHandler):
    def read(self, request):
        legislator_fields = {'sources': 0, 'roles': 0, 'old_roles': 0}
        # replace with request's fields if they exist
        legislator_fields = _build_field_list(request, legislator_fields)

        _filter = _build_mongo_filter(request, ('state', 'first_name',
                                               'last_name'))
        elemMatch = _build_mongo_filter(request, ('chamber', 'term',
                                                  'district', 'party'))
        if elemMatch:
            _filter['roles'] = {'$elemMatch': elemMatch}

        active = request.GET.get('active')
        if not active and 'term' not in request.GET:
            # Default to only searching active legislators if no term
            # is supplied
            _filter['active'] = True
        elif active and active.lower() == 'true':
            _filter['active'] = True

        return list(db.legislators.find(_filter, legislator_fields))


class CommitteeHandler(BillyHandler):
    def read(self, request, id):
        return db.committees.find_one({'_all_ids': id},
                                     _build_field_list(request))


class CommitteeSearchHandler(BillyHandler):
    def read(self, request):
        committee_fields = {'members': 0, 'sources': 0}
        # replace with request's fields if they exist
        committee_fields = _build_field_list(request, committee_fields)

        _filter = _build_mongo_filter(request, ('committee', 'subcommittee',
                                                'chamber', 'state'))
        return list(db.committees.find(_filter, committee_fields))


class StatsHandler(BillyHandler):
    def read(self, request):
        counts = {}

        # db.counts contains the output of a m/r run that generates counts of
        # bills and bill sub-objects
        for count in db.counts.find():
            val = count['value']
            abbr = count['_id']

            if abbr == 'total':
                val['legislators'] = db.legislators.count()
            else:
                level = metadata(abbr)['level']
                val['legislators'] = db.legislators.find({'level': level,
                                                          level: abbr}).count()

            counts[abbr] = val

        stats = db.command('dbStats')
        stats['counts'] = counts

        return stats


class EventsHandler(BillyHandler):
    def read(self, request, id=None, events=[]):
        if events:
            return events

        if id:
            return db.events.find_one({'_id': id})

        spec = {}

        for key in ('state', 'type'):
            value = request.GET.get(key)
            if not value:
                continue

            split = value.split(',')

            if len(split) == 1:
                spec[key] = value
            else:
                spec[key] = {'$in': split}

        invalid_date = False

        if 'dtstart' in request.GET:
            try:
                spec['when'] = {'$gte': parse_param_dt(request.GET['dtstart'])}
            except ValueError:
                invalid_date = True
        else:
            # By default, go back 7 days
            now = datetime.datetime.now()
            before = now - datetime.timedelta(7)
            spec['when'] = {'$gte': before}

        if 'dtend' in request.GET:
            try:
                spec['when']['$lte'] = parse_param_dt(request.GET['dtend'])
            except ValueError:
                invalid_date = True

        if invalid_date:
            resp = rc.BAD_REQUEST
            resp.write(": invalid updated_since parameter."
                       " Please supply a date in YYYY-MM-DD format.")
            return resp

        return list(db.events.find(spec).sort(
            'when', pymongo.ASCENDING).limit(1000))


class SubjectListHandler(BillyHandler):
    def read(self, request, abbr, session=None, chamber=None):
        abbr = abbr.lower()
        level = metadata(abbr)['level']
        spec = {level: abbr}
        if session:
            spec['session'] = session
        if chamber:
            chamber = chamber.lower()
            spec['chamber'] = _chamber_aliases.get(chamber, chamber)
        result = {}
        for subject in settings.BILLY_SUBJECTS:
            count = db.bills.find(dict(spec, subjects=subject)).count()
            result[subject] = count
        return result


class ReconciliationHandler(BaseHandler):
    """
    An endpoint compatible with the Google Refine 2.0 reconciliation API.

    Given a query containing a legislator name along with some optional
    filtering properties ("state", "chamber"), this handler will return
    a list of possible matching legislators.

    See http://code.google.com/p/google-refine/wiki/ReconciliationServiceApi
    for the API specification.
    """
    allowed_methods = ('GET', 'POST')
    key = getattr(settings, 'SUNLIGHT_SERVICES_KEY', 'no-key')

    metadata = {
        "name": "Billy Reconciliation Service",
        "view": {
            "url": "%slegislators/preview/{{id}}/?apikey=%s" % (
                settings.API_BASE_URL, key),
            },
        "preview": {
            "url": "%slegislators/preview/{{id}}/?apikey=%s" % (
                settings.API_BASE_URL, key),
            "width": 430,
            "height": 300
            },
        "defaultTypes": [
            {"id": "/billy/legislator",
             "name": "Legislator"}],
        }

    def read(self, request):
        return self.reconcile(request)

    def create(self, request):
        return self.reconcile(request)

    def reconcile(self, request):
        query = request.GET.get('query') or request.POST.get('query')

        if query:
            # If the query doesn't start with a '{' then it's a simple
            # string that should be used as the query w/ no extra params
            if not query.startswith("{"):
                query = '{"query": "%s"}' % query
            query = json.loads(query)

            return {"result": self.results(query)}

        # Batch query mode
        queries = request.GET.get('queries') or request.POST.get('queries')

        if queries:
            queries = json.loads(queries)
            ret = {}
            for key, value in queries.items():
                ret[key] = {'result': self.results(value)}

            return ret

        # If no queries, return metadata
        return self.metadata

    def results(self, query):
        # Look for the query to be a substring of a legislator name
        # (case-insensitive)
        pattern = re.compile(".*%s.*" % query['query'],
                             re.IGNORECASE)

        spec = {'full_name': pattern}

        for prop in query.get('properties', []):
            # Allow filtering by state or chamber for now
            if prop['pid'] in ('state', 'chamber'):
                spec[prop['pid']] = prop['v']

        legislators = db.legislators.find(spec)

        results = []
        for leg in legislators:
            if legislators.count() == 1:
                match = True
                score = 100
            else:
                match = False
                if leg['last_name'] == query['query']:
                    score = 90
                else:
                    distance = levenshtein_distance(leg['full_name'].lower(),
                                                    query['query'].lower())
                    score = 100.0 / (1 + distance)

            # Note: There's a bug in Refine that causes reconciliation
            # scores to be overwritten if the same legislator is returned
            # for multiple queries. see:
            # http://code.google.com/p/google-refine/issues/detail?id=185

            results.append({"id": leg['_id'],
                            "name": leg['full_name'],
                            "score": score,
                            "match": match,
                            "type": [
                                {"id": "/billy/legislator",
                                 "name": "Legislator"}]})

        return sorted(results, cmp=lambda l, r: cmp(r['score'], l['score']))


class LegislatorGeoHandler(BillyHandler):
    base_url = getattr(settings, 'BOUNDARY_SERVICE_URL',
                       'http://localhost:8001/1.0/')

    def read(self, request):
        latitude, longitude = request.GET.get('lat'), request.GET.get('long')

        if not latitude or not longitude:
            resp = rc.BAD_REQUEST
            resp.write(': Need lat and long parameters')
            return resp

        url = "%sboundary/?contains=%s,%s&sets=sldl,sldu&limit=0" % (
            self.base_url, latitude, longitude)

        resp = json.load(urllib2.urlopen(url))

        filters = []
        for dist in resp['objects']:
            state = dist['name'][0:2].lower()
            chamber = {'/1.0/boundary-set/sldu/': 'upper',
                       '/1.0/boundary-set/sldl/': 'lower'}[dist['set']]
            census_name = dist['slug']

            # look up district slug
            districts = db.districts.find({'chamber': chamber,
                                           'boundary_id': census_name})
            count = districts.count()
            if count == 1:
                filters.append({'state': state,
                                'district': districts[0]['name'],
                                'chamber': chamber})

        if not filters:
            return []

        return list(db.legislators.find({'$or': filters},
                                        _build_field_list(request)))


class DistrictHandler(BillyHandler):

    def read(self, request, abbr, chamber=None):
        filter = {'abbr': abbr}
        if not chamber:
            chamber = {'$exists': True}
        filter['chamber'] = chamber
        districts = list(db.districts.find(filter))

        # change leg filter
        filter['state'] = filter.pop('abbr')
        filter['active'] = True
        legislators = db.legislators.find(filter, fields={'_id': 0,
                                                          'leg_id': 1,
                                                          'chamber': 1,
                                                          'district': 1,
                                                          'full_name': 1})

        leg_dict = defaultdict(list)
        for leg in legislators:
            leg_dict[(leg['chamber'], leg['district'])].append(leg)
            leg.pop('chamber')
            leg.pop('district')
        for dist in districts:
            dist['legislators'] = leg_dict[(dist['chamber'], dist['name'])]

        return districts


class BoundaryHandler(BillyHandler):
    base_url = getattr(settings, 'BOUNDARY_SERVICE_URL',
                       'http://localhost:8001/1.0/')


    def read(self, request, boundary_id):
        url = "%sshape/%s/" % (self.base_url, boundary_id)
        try:
            data = json.load(urllib2.urlopen(url))
        except urllib2.HTTPError, e:
            if 400 <= e.code < 500:
                resp = rc.NOT_FOUND
                return resp
            else:
                raise e

        shape = data['shape']
        centroid = data['centroid']['coordinates']

        all_lon = []
        all_lat = []
        for shape in data['shape']['coordinates']:
            for coord_set in shape:
                all_lon.extend(c[0] for c in coord_set)
                all_lat.extend(c[1] for c in coord_set)
        lon_delta = abs(max(all_lon) - min(all_lon))
        lat_delta = abs(max(all_lat) - min(all_lat))

        region = {'center_lon': centroid[0], 'center_lat': centroid[1],
                  'lon_delta': lon_delta, 'lat_delta': lat_delta,
                 }

        district = db.districts.find_one({'boundary_id': boundary_id})
        district['shape'] = shape
        district['region'] = region

        return district
