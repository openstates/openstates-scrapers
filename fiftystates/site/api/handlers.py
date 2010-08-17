import re
import datetime

from fiftystates.backend import db
from fiftystates.site import search
from fiftystates.site.geo.models import District

from django.http import HttpResponse

from piston.utils import rc
from piston.handler import BaseHandler, HandlerMetaClass


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
                    if obj.get('_type') == 'person' and '_id' in obj:
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

def _build_mongo_filter(request, keys, icase=True):
    # We use regex queries to get case insensitive search - this
    # means they won't use any indexes for now. Real case insensitive
    # queries are coming eventually:
    # http://jira.mongodb.org/browse/SERVER-90
    _filter = {}
    for key in keys:
        value = request.GET.get(key)
        if value:
            _filter[key] = re.compile('^%s$' % value, re.IGNORECASE)
    return _filter

class FiftyStateHandler(BaseHandler):
    """
    Base handler for the Fifty State API.
    """
    __metaclass__ = FiftyStateHandlerMetaClass
    allowed_methods = ('GET',)


class BillHandler(FiftyStateHandler):
    def read(self, request, state, session, chamber, bill_id):
        return db.bills.find_one({'state': state.lower(),
                                  'session': session,
                                  'chamber': chamber.lower(),
                                  'bill_id': bill_id})


class StateHandler(FiftyStateHandler):
    def read(self, request, state):
        """
        Get metadata about a state legislature.
        """
        return db.metadata.find_one({'_id': state.lower()})


class CommitteeHandler(FiftyStateHandler):
    def read(self, request, id):
        return db.committees.find_one({'_all_ids': id})


class LegislatorHandler(FiftyStateHandler):
    def read(self, request, id):
        return db.legislators.find_one({'_all_ids': id})


class LegislatorSearchHandler(FiftyStateHandler):
    def read(self, request):
        _filter = _build_mongo_filter(request, ('state', 'first_name',
                                               'last_name'))
        elemMatch = _build_mongo_filter(request, ('chamber', 'term',
                                                  'district', 'party'))
        _filter['roles'] = {'$elemMatch': elemMatch}

        return list(db.legislators.find(_filter))


class CommitteeSearchHandler(FiftyStateHandler):
    def read(self, request):
        _filter = _build_mongo_filter(request, ('committee', 'subcommittee',
                                                'chamber', 'state'))
        return list(db.committees.find(_filter))


class DistrictGeoHandler(FiftyStateHandler):
    def read(self, request, state, session, chamber):
        try:
            district = District.lat_long(request.GET['lat'],
                                         request.GET['long']).get(
                state_abbrev=state,
                chamber=chamber)
            district.session = session
            return district
        except District.DoesNotExist:
            return rc.NOT_HERE
        except KeyError:
            resp = rc.BAD_REQUEST
            resp.write(": Need lat and long parameters")
            return resp


class BillSearchHandler(FiftyStateHandler):
    def read(self, request):

        query = request.GET.get('q')
        if not query:
            resp = rc.BAD_REQUEST
            resp.write(": Need a query string")
            return resp

        return search.bill_query(query, request.GET)
