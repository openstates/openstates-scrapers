import datetime
from django.conf import settings
from django.conf.urls.defaults import *
from django.http import HttpResponse

from locksmith.mongoauth.db import db

import piston.resource
from piston.emitters import Emitter

from billy.site.api import handlers
from billy.site.api.views import legislator_preview
from billy.site.api.emitters import BillyJSONEmitter, BillyXMLEmitter
from billy.site.api.emitters import FeedEmitter, ICalendarEmitter

if getattr(settings, 'USE_LOCKSMITH', False):
    from locksmith.mongoauth.authentication import PistonKeyAuthentication

    class Authorizer(PistonKeyAuthentication):
        def challenge(self):
            resp = HttpResponse("Authorization Required: \n"
        "obtain a key at http://services.sunlightlabs.com/accounts/register/")
            resp.status_code = 401
            return resp

    authorizer = Authorizer()

    class Resource(piston.resource.Resource):
        def __call__(self, request, *args, **kwargs):
            resp = super(Resource, self).__call__(request, *args, **kwargs)

            try:
                db.logs.insert({'key': request.apikey['_id'],
                                'method': self.handler.__class__.__name__,
                                'query_string': request.META['QUERY_STRING'],
                                'timestamp': datetime.datetime.utcnow()})
            except AttributeError:
                pass

            return resp
else:
    authorizer = None
    Resource = piston.resource.Resource

Emitter.register('json', BillyJSONEmitter, 'application/json; charset=utf-8')
Emitter.register('xml', BillyXMLEmitter, 'application/xml; charset=utf-8')

Emitter.register('rss', FeedEmitter, 'application/rss+xml')
Emitter.register('ics', ICalendarEmitter, 'text/calendar')

Emitter.unregister('yaml')
Emitter.unregister('django')
Emitter.unregister('pickle')

all_metadata_handler = Resource(handlers.AllMetadataHandler,
                                authentication=authorizer)
metadata_handler = Resource(handlers.MetadataHandler,
                            authentication=authorizer)
bill_handler = Resource(handlers.BillHandler,
                        authentication=authorizer)
bill_search_handler = Resource(handlers.BillSearchHandler,
                               authentication=authorizer)
legislator_handler = Resource(handlers.LegislatorHandler,
                              authentication=authorizer)
legsearch_handler = Resource(handlers.LegislatorSearchHandler,
                             authentication=authorizer)
committee_handler = Resource(handlers.CommitteeHandler,
                             authentication=authorizer)
committee_search_handler = Resource(handlers.CommitteeSearchHandler,
                                    authentication=authorizer)
stats_handler = Resource(handlers.StatsHandler,
                         authentication=authorizer)
events_handler = Resource(handlers.EventsHandler,
                          authentication=authorizer)
subject_list_handler = Resource(handlers.SubjectListHandler,
                                authentication=authorizer)
reconciliation_handler = Resource(handlers.ReconciliationHandler,
                                  authentication=authorizer)
legislator_geo_handler = Resource(handlers.LegislatorGeoHandler,
                                      authentication=authorizer)
district_handler = Resource(handlers.DistrictHandler,
                            authentication=authorizer)
boundary_handler = Resource(handlers.BoundaryHandler,
                            authentication=authorizer)

urlpatterns = patterns('',
    # metadata
    url(r'^v1/metadata/$', all_metadata_handler),
    url(r'^v1/metadata/(?P<abbr>[a-zA-Z]{2,2})/$', metadata_handler),

    # two urls for bill handler
    url(r'^v1/bills/(?P<abbr>[a-zA-Z]{2,2})/(?P<session>.+)/'
        r'(?P<chamber>upper|lower)/(?P<bill_id>.+)/$', bill_handler),
    url(r'^v1/bills/(?P<abbr>[a-zA-Z]{2,2})/(?P<session>.+)/'
        r'(?P<bill_id>.+)/$', bill_handler),
    url(r'^v1/bills/$', bill_search_handler),

    url(r'^v1/legislators/(?P<id>[A-Z]{2,2}L\d{6,6})/$', legislator_handler),
    url(r'^v1/legislators/$', legsearch_handler),

    url(r'^v1/committees/(?P<id>[A-Z]{2,2}C\d{6,6})/$', committee_handler),
    url(r'^v1/committees/$', committee_search_handler),

    url(r'^v1/events/$', events_handler),
    url(r'^v1/events/(?P<id>[A-Z]{2,2}E\d{8,8})/$', events_handler),

    url(r'v1/subject_counts/(?P<abbr>[a-zA-Z]{2,2})/(?P<session>.+)/(?P<chamber>upper|lower)/', subject_list_handler),
    url(r'v1/subject_counts/(?P<abbr>[a-zA-Z]{2,2})/(?P<session>.+)/',
        subject_list_handler),
    url(r'v1/subject_counts/(?P<abbr>[a-zA-Z]{2,2})/', subject_list_handler),

    url(r'^v1/legislators/reconcile/$', reconciliation_handler),
    url(r'^v1/legislators/preview/(?P<id>[A-Z]{2,2}L\d{6,6})/$',
        legislator_preview),

    url(r'v1/legislators/geo/$', legislator_geo_handler),

    # districts & boundaries
    url(r'v1/districts/(?P<abbr>[a-zA-Z]{2})/$',
        district_handler),
    url(r'v1/districts/(?P<abbr>[a-zA-Z]{2})/(?P<chamber>upper|lower)/$',
        district_handler),
    url(r'v1/districts/boundary/(?P<boundary_id>.+)/$', boundary_handler),


    url(r'^v1/stats/$', stats_handler),
)
