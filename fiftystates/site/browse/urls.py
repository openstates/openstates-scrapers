from django.conf.urls.defaults import *

urlpatterns = patterns('fiftystates.site.browse.views',
    (r'^$', 'index'),
    (r'^(?P<state>[a-zA-Z]{2,2})/$', 'state_index'),
    (r'^(?P<state>[a-zA-Z]{2,2})/(?P<session>.+)/'
     r'(?P<chamber>upper|lower|house|assembly|senate)/'
     r'(?P<id>.*)$', 'bill'),
    (r'^(people|legislators)/(?P<id>.*)/$', 'legislator'),
)
