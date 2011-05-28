from django.conf.urls.defaults import *

urlpatterns = patterns('billy.site.browse.views',
    url(r'^$', 'browse_index'),
    url(r'^(?P<abbr>[a-zA-Z]{2})/$', 'overview'),
    url(r'^(?P<abbr>[a-zA-Z]{2})/bills/$', 'bills'),
    url(r'^(?P<abbr>[a-zA-Z]{2})/random_bill/$', 'random_bill'),
    url(r'^(?P<abbr>[a-zA-Z]{2})/(?P<session>.+)/(?P<id>.*)/$', 'bill',
        name='bill'),
    url(r'^(?P<abbr>[a-zA-Z]{2})/legislators/$', 'legislators'),
    url(r'^(?P<abbr>[a-zA-Z]{2})/committees/$', 'committees'),
    url(r'^legislators/(?P<id>.*)/$', 'legislator'),
)
