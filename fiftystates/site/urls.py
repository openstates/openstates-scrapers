from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin


urlpatterns = patterns('',
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^api/locksmith/', include('locksmith.auth.urls')),
    (r'^api/', include('fiftystates.site.api.urls')),
    (r'^browse/', include('fiftystates.site.browse.urls')),
    (r'^data/(?P<state>\w\w).zip$', 'fiftystates.site.api.views.data_zip'),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT,
          'show_indexes': True}))
