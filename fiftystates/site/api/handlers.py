import re
import datetime

from fiftystates.backend import db
from fiftystates.site import search
from fiftystates.site.geo.models import District
from fiftystates.utils import keywordize

from django.http import HttpResponse

from piston.utils import rc
from piston.handler import BaseHandler, HandlerMetaClass


_chamber_aliases = {
    'assembly': 'lower',
    'house': 'lower',
    'senate': 'upper',
    }


def _build_mongo_filter(request, keys, icase=True):
    # We use regex queries to get case insensitive search - this
    # means they won't use any indexes for now. Real case insensitive
    # queries are coming eventually:
    # http://jira.mongodb.org/browse/SERVER-90
    _filter = {}
    for key in keys:
        value = request.GET.get(key)
        if value:
            if key == 'chamber':
                value = value.lower()
                _filter[key] = _chamber_aliases.get(value, value)
            else:
                _filter[key] = re.compile('^%s$' % value, re.IGNORECASE)
    return _filter


class FiftyStateHandlerMetaClass(HandlerMetaClass):
    """
    Scrubs internal fields (those starting with '_') from Handler results
    and returns HTTP error if Handler result is None.
    """
    def __new__(cls, name, bases, attrs):
        new_cls = super(FiftyStateHandlerMetaClass, cls).__new__(
            cls, name, bases, attrs)

        if hasattr(new_cls, 'read'):

            def clean(obj):
                if isinstance(obj, dict):
                    if (obj.get('_type') in ('person', 'committee') and
                        '_id' in obj):
                        obj['id'] = obj['_id']

                    for key, value in obj.items():
                        if key.startswith('_'):
                            del obj[key]
                        else:
                            obj[key] = clean(value)
                elif isinstance(obj, list):
                    obj = [clean(item) for item in obj]
                elif hasattr(obj, '__dict__'):
                    for key, value in obj.__dict__.items():
                        if key.startswith('_'):
                            del obj.__dict__[key]
                        else:
                            obj.__dict__[key] = clean(value)
                return obj

            old_read = new_cls.read

            def new_read(*args, **kwargs):
                obj = old_read(*args, **kwargs)
                if isinstance(obj, HttpResponse):
                    return obj

                if obj is None:
                    return rc.NOT_FOUND

                return clean(obj)

            new_cls.read = new_read

        return new_cls


class FiftyStateHandler(BaseHandler):
    """
    Base handler for the Fifty State API.
    """
    __metaclass__ = FiftyStateHandlerMetaClass
    allowed_methods = ('GET',)


class MetadataHandler(FiftyStateHandler):
    def read(self, request, state):
        """
        Get metadata about a state legislature.
        """
        return db.metadata.find_one({'_id': state.lower()})


class BillHandler(FiftyStateHandler):
    def read(self, request, state, session, bill_id, chamber=None):
        query = {'state': state.lower(), 'session': session,
                 'bill_id': bill_id}
        if chamber:
            query['chamber'] = chamber.lower()
        return db.bills.find_one(query)


class BillSearchHandler(FiftyStateHandler):
    def read(self, request):

        bill_fields = {'title': 1, 'created_at': 1, 'updated_at': 1,
                       'bill_id': 1, 'type': 1, 'state': 1,
                       'session': 1, 'chamber': 1}

        # normal mongo search logic
        _filter = _build_mongo_filter(request, ('state', 'chamber'))

        # process full-text query
        query = request.GET.get('q')
        if query:
            keywords = list(keywordize(query))
            _filter['_keywords'] = {'$all': keywords}

        # process search_window
        search_window = request.GET.get('search_window', '').lower()
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
                _filter['since'] = datetime.datetime.strptime(since,
                                                          "%Y-%m-%d %H:%M")
            except ValueError:
                try:
                    _filter['since'] = datetime.datetime.strptime(since,
                                                               "%Y-%m-%d")
                except ValueError:
                    resp = rc.BAD_REQUEST
                    resp.write(": invalid updated_since parameter."
                    " Please supply a date in YYYY-MM-DD format.")
                    return resp

        return list(db.bills.find(_filter, bill_fields))


class LegislatorHandler(FiftyStateHandler):
    def read(self, request, id):
        return db.legislators.find_one({'_all_ids': id})


class LegislatorSearchHandler(FiftyStateHandler):
    def read(self, request):
        legislator_fields = {'sources': 0, 'roles': 0}

        _filter = _build_mongo_filter(request, ('state', 'first_name',
                                               'last_name'))
        elemMatch = _build_mongo_filter(request, ('chamber', 'term',
                                                  'district', 'party'))
        _filter['roles'] = {'$elemMatch': elemMatch}

        active = request.GET.get('active')
        if not active and 'term' not in request.GET:
            # Default to only searching active legislators if no term
            # is supplied
            _filter['active'] = True
        elif active:
            _filter['active'] = (active.lower() == 'true')

        return list(db.legislators.find(_filter, legislator_fields))


class LegislatorGeoHandler(FiftyStateHandler):
    def read(self, request):
        try:
            districts = District.lat_long(request.GET['lat'],
                                          request.GET['long'])
            filters = []
            for d in districts:
                filters.append({'state': d.state_abbrev,
                                'roles': {'$elemMatch': {'district':d.name,
                                                         'chamber':d.chamber}}}
                              )
            return list(db.legislators.find({'$or': filters}))
        except District.DoesNotExist:
            return rc.NOT_HERE
        except KeyError:
            resp = rc.BAD_REQUEST
            resp.write(": Need lat and long parameters")
            return resp


class CommitteeHandler(FiftyStateHandler):
    def read(self, request, id):
        return db.committees.find_one({'_all_ids': id})


class CommitteeSearchHandler(FiftyStateHandler):
    def read(self, request):
        committee_fields = {'members': 0, 'sources': 0}

        _filter = _build_mongo_filter(request, ('committee', 'subcommittee',
                                                'chamber', 'state'))
        return list(db.committees.find(_filter, committee_fields))

