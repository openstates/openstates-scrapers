from django.conf.urls.defaults import *

urlpatterns = patterns('billy.site.browse.views',
    url(r'^$', 'all_states'),
    url(r'^(?P<state>[a-zA-Z]{2})/$', 'state_index'),
    url(r'^(?P<state>[a-zA-Z]{2})/bills/$', 'bills'),
    url(r'^(?P<state>[a-zA-Z]{2})/random_bill/$', 'random_bill'),
    url(r'^(?P<state>[a-zA-Z]{2})/(?P<session>.+)/(?P<id>.*)/$', 'bill',
        name='bill'),
    url(r'^(?P<state>[a-zA-Z]{2})/legislators/$', 'legislators'),
    url(r'^(?P<state>[a-zA-Z]{2})/committees/$', 'committees'),
    url(r'^legislators/(?P<id>.*)/$', 'legislator'),
)
