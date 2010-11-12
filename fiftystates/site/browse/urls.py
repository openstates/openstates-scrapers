from django.conf.urls.defaults import *

urlpatterns = patterns('fiftystates.site.browse.views',
    url(r'^(?P<state>[a-zA-Z]{2})/$', 'state_index'),
    url(r'^(?P<state>[a-zA-Z]{2})/random_bill/$', 'random_bill'),
    url(r'^(?P<state>[a-zA-Z]{2})/(?P<session>.+)/(?P<id>.*)/$', 'bill',
        name='bill'),
    url(r'^legislators/(?P<id>.*)/$', 'legislator'),
)
