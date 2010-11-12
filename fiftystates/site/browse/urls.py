from django.conf.urls.defaults import *

urlpatterns = patterns('fiftystates.site.browse.views',
    url(r'^(?P<state>[a-zA-Z]{2,2})/$', 'state_index'),
    url(r'^(?P<state>[a-zA-Z]{2})/(?P<session>.+)/'
     r'(?P<chamber>upper|lower|house|assembly|senate)/(?P<id>.*)$', 'bill'),
    url(r'^legislators/(?P<id>.*)/$', 'legislator'),
)
