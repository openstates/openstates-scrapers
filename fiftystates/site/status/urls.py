from django.conf.urls.defaults import *

urlpatterns = patterns('fiftystates.site.status.views',
    url(r'^$', 'status_index', name='status_index'),
    url(r'^map.svg$', 'map_svg', name='map_svg'),
)
