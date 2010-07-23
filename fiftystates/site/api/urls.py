from django.conf import settings
from django.conf.urls.defaults import *

from piston.resource import Resource
from piston.emitters import Emitter

from fiftystates.site.api.handlers import *
from fiftystates.site.api.emitters import LoggingJSONEmitter

if getattr(settings, 'USE_LOCKSMITH', False):
    from locksmith.auth.authentication import PistonKeyAuthentication
    authorizer = PistonKeyAuthentication()
    Emitter.register('json', LoggingJSONEmitter, 'application/json; charset=utf-8')
else:
    authorizer = None

bill_handler = Resource(BillHandler, authentication=authorizer)
state_handler = Resource(StateHandler, authentication=authorizer)
committee_handler = Resource(CommitteeHandler, authentication=authorizer)
legislator_handler = Resource(LegislatorHandler, authentication=authorizer)
legsearch_handler = Resource(LegislatorSearchHandler,
                             authentication=authorizer)
district_handler = Resource(DistrictHandler, authentication=authorizer)
district_geo_handler = Resource(DistrictGeoHandler,
                                authentication=authorizer)
latest_bills_handler = Resource(LatestBillsHandler,
                                authentication=authorizer)
bill_search_handler = Resource(BillSearchHandler, authentication=authorizer)

urlpatterns = patterns('',
    url(r'^(?P<state>[a-zA-Z]{2,2})/(?P<session>.+)/'
        r'(?P<chamber>upper|lower)/bills/(?P<bill_id>.+)/$', bill_handler),
    url(r'^(?P<state>[a-zA-Z]{2,2})/(?P<session>.+)/'
        r'(?P<chamber>upper|lower)/districts/geo/$', district_geo_handler),
    url(r'^(?P<state>[a-zA-Z]{2,2})/(?P<session>.+)/'
        r'(?P<chamber>upper|lower)/districts/(?P<district>.+)/$',
        district_handler),
    url(r'^(?P<state>[a-zA-Z]{2,2})/$', state_handler),
    url(r'^committees/(?P<id>[A-Z]{2,2}C\d{6,6})/$', committee_handler),
    url(r'^legislators/(?P<id>[A-Z]{2,2}L\d{6,6})/$', legislator_handler),
    url(r'^legislators/search/$', legsearch_handler),
    url(r'^bills/latest/$', latest_bills_handler),
    url(r'^bills/search/$', bill_search_handler),
)
