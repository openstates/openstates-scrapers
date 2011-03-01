from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin


urlpatterns = patterns('',
    (r'^api/locksmith/', include('locksmith.auth.urls')),
    (r'^api/', include('billy.site.api.urls')),
    (r'^browse/', include('billy.site.browse.urls')),
    (r'^downloads/$', 'billy.site.api.views.downloads'),
    (r'^data/(?P<state>\w\w).zip$', 'billy.site.api.views.data_zip'),

    # flat pages
    (r'^$', 'django.views.generic.simple.direct_to_template',
     {'template':'index.html'}),
    (r'^contributing/$', 'django.views.generic.simple.direct_to_template',
     {'template':'contributing.html'}),
    (r'^thanks/$', 'django.views.generic.simple.direct_to_template',
     {'template':'thankyou.html'}),
    (r'^categorization/$', 'django.views.generic.simple.direct_to_template',
     {'template':'categorization.html'}),
    (r'^status/$', 'django.views.generic.simple.direct_to_template',
     {'template':'status.html'}),

    # api docs
    (r'^api/$', 'django.views.generic.simple.direct_to_template',
     {'template':'api.html'}),
    (r'^api/changelog/$', 'django.views.generic.simple.direct_to_template',
     {'template':'api_changelog.html'}),
    (r'^api/metadata/$', 'django.views.generic.simple.direct_to_template',
     {'template':'api_metadata.html'}),
    (r'^api/bills/$', 'django.views.generic.simple.direct_to_template',
     {'template':'api_bills.html'}),
    (r'^api/committees/$', 'django.views.generic.simple.direct_to_template',
     {'template':'api_committees.html'}),
    (r'^api/legislators/$', 'django.views.generic.simple.direct_to_template',
     {'template':'api_legislators.html'}),
    (r'^api/events/$', 'django.views.generic.simple.direct_to_template',
     {'template':'api_events.html'}),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT,
          'show_indexes': True}))
