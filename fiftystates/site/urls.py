from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin


urlpatterns = patterns('',
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^geo/', include('fiftystates.site.geo.urls')),
    (r'^api/locksmith/', include('locksmith.auth.urls')),
    (r'^api/', include('fiftystates.site.api.urls')),
    (r'^status/', include('fiftystates.site.status.urls')),
    (r'^browse/', include('fiftystates.site.browse.urls')),
)

if settings.DEBUG:
    print settings.MEDIA_ROOT
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT,
          'show_indexes': True}))
