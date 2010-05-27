from django.conf.urls.defaults import *

urlpatterns = patterns('fiftystates.site.geo.views',
    (r'^district/(?P<state>[a-zA-Z]{2,2})/(?P<chamber>upper|lower)'
     r'/(?P<name>.*).kml$', 'district_kml'),
    (r'^chamber/(?P<state>[a-zA-Z]{2,2})/(?P<chamber>upper|lower).kml$',
     'chamber_kml'),
)
