from django.conf.urls.defaults import patterns, include
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',

    # flat pages
    (r'^about/$', 'django.views.generic.simple.direct_to_template',
     {'template':'flat/about.html'}),
    (r'^methodology/$', 'django.views.generic.simple.direct_to_template',
     {'template':'flat/methodology.html'}),
    (r'^contributing/$', 'django.views.generic.simple.direct_to_template',
     {'template':'flat/contributing.html'}),
    (r'^thanks/$', 'django.views.generic.simple.direct_to_template',
     {'template':'flat/thanks.html'}),
    (r'^contact/$', 'django.views.generic.simple.direct_to_template',
     {'template':'flat/contact.html'}),
    (r'^categorization/$', 'django.views.generic.simple.direct_to_template',
     {'template':'flat/categorization.html'}),
    (r'^csv_downloads/$', 'django.views.generic.simple.direct_to_template',
     {'template':'flat/csv_downloads.html'}),
    (r'^reportcard/$', 'django.views.generic.simple.direct_to_template',
     {'template':'flat/reportcard.html'}),
    (r'^map_svg/$', 'django.views.generic.simple.direct_to_template',
     {'template':'flat/openstatesmap.svg'}),

    # api docs
    (r'^api/$', 'django.views.generic.simple.direct_to_template',
     {'template':'flat/api/api.html'}),
    (r'^api/metadata/$', 'django.views.generic.simple.direct_to_template',
     {'template':'flat/api/metadata.html'}),
    (r'^api/bills/$', 'django.views.generic.simple.direct_to_template',
     {'template':'flat/api/bills.html'}),
    (r'^api/committees/$', 'django.views.generic.simple.direct_to_template',
     {'template':'flat/api/committees.html'}),
    (r'^api/legislators/$', 'django.views.generic.simple.direct_to_template',
     {'template':'flat/api/legislators.html'}),
    (r'^api/events/$', 'django.views.generic.simple.direct_to_template',
     {'template':'flat/api/events.html'}),
    (r'^api/districts/$', 'django.views.generic.simple.direct_to_template',
     {'template':'flat/api/districts.html'}),

    # locksmith & sunlightauth
    (r'^api/locksmith/', include('locksmith.mongoauth.urls')),
    (r'', include('sunlightauth.urls')),

    (r'^api/', include('billy.web.api.urls')),
    (r'^admin/', include('billy.web.admin.urls')),
    (r'^djadmin/', include(admin.site.urls)),
    (r'^', include('billy.web.public.urls')),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^404/$', 'django.views.defaults.page_not_found'),
        (r'^500/$', 'django.views.defaults.server_error'),
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': settings.STATIC_ROOT,
          'show_indexes': True}))
