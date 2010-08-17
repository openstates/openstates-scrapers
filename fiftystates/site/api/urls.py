from django.conf import settings
from django.conf.urls.defaults import *

from piston.resource import Resource
from piston.emitters import Emitter

from fiftystates.site.api.handlers import *
from fiftystates.site.api.emitters import LoggingJSONEmitter
from fiftystates.site.api.views import document

if getattr(settings, 'USE_LOCKSMITH', False):
    from locksmith.auth.authentication import PistonKeyAuthentication
    authorizer = PistonKeyAuthentication()
    Emitter.register('json', LoggingJSONEmitter,
                     'application/json; charset=utf-8')
else:
    authorizer = None

bill_handler = Resource(BillHandler, authentication=authorizer)
metadata_handler = Resource(MetadataHandler, authentication=authorizer)
committee_handler = Resource(CommitteeHandler, authentication=authorizer)
committee_search_handler = Resource(CommitteeSearchHandler,
                                    authentication=authorizer)
legislator_handler = Resource(LegislatorHandler, authentication=authorizer)
legsearch_handler = Resource(LegislatorSearchHandler,
                             authentication=authorizer)
legislator_geo_handler = Resource(LegislatorGeoHandler,
                                  authentication=authorizer)
bill_search_handler = Resource(BillSearchHandler, authentication=authorizer)

urlpatterns = patterns('',
    url(r'^(?P<state>[a-zA-Z]{2,2})/(?P<session>.+)/'
        r'(?P<chamber>upper|lower)/bills/(?P<bill_id>.+)/$', bill_handler),
    url(r'^(?P<state>[a-zA-Z]{2,2})/$', metadata_handler),
    url(r'^committees/(?P<id>[A-Z]{2,2}C\d{6,6})/$', committee_handler),
    url(r'^legislators/(?P<id>[A-Z]{2,2}L\d{6,6})/$', legislator_handler),
    url(r'^legislators/search/$', legsearch_handler),
    url(r'^bills/search/$', bill_search_handler),
    url(r'^documents/(?P<id>[A-Z]{2,2}D\d{8,8})/$', document),

    # v1 urls
    url(r'^v1/metadata/(?P<state>[a-zA-Z]{2,2})/$', metadata_handler),

    url(r'^v1/bills/(?P<state>[a-zA-Z]{2,2})/(?P<session>.+)/'
        r'(?P<chamber>upper|lower)/(?P<bill_id>.+)/$', bill_handler),
    url(r'^v1/bills/$', bill_search_handler),

    url(r'^v1/legislators/(?P<id>[A-Z]{2,2}L\d{6,6})/$', legislator_handler),
    url(r'^v1/legislators/$', legsearch_handler),
    url(r'^v1/legislators/geo/$', legislator_geo_handler),

    url(r'^v1/committees/(?P<id>[A-Z]{2,2}C\d{6,6})/$', committee_handler),
    url(r'^v1/committees/$', committee_search_handler),
)
