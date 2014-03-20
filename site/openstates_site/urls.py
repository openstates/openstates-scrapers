from django.conf.urls import patterns, include
from django.conf import settings
from django.views.generic.base import RedirectView
from django.views.generic import TemplateView

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',

    # flat pages
    (r'^about/$', TemplateView.as_view(template_name='flat/about.html')),
    (r'^methodology/$', TemplateView.as_view(template_name='flat/methodology.html')),
    (r'^contributing/$', TemplateView.as_view(template_name='flat/contributing.html')),
    (r'^thanks/$', TemplateView.as_view(template_name='flat/thanks.html')),
    (r'^contact/$', TemplateView.as_view(template_name='flat/contact.html')),
    (r'^categorization/$', TemplateView.as_view(template_name='flat/categorization.html')),
    (r'^csv_downloads/$', TemplateView.as_view(template_name='flat/csv_downloads.html')),
    (r'^reportcard/$', TemplateView.as_view(template_name='flat/reportcard.html')),
    (r'^map_svg/$', TemplateView.as_view(template_name='flat/openstatesmap.svg')),

    # api docs
    (r'^api/$', RedirectView.as_view(url='http://sunlightlabs.github.io/openstates-api/')),
    (r'^api/metadata/$', RedirectView.as_view(url='http://sunlightlabs.github.io/openstates-api/metadata.html')),
    (r'^api/bills/$', RedirectView.as_view(url='http://sunlightlabs.github.io/openstates-api/bills.html')),
    (r'^api/committees/$', RedirectView.as_view(url='http://sunlightlabs.github.io/openstates-api/committees.html')),
    (r'^api/legislators/$', RedirectView.as_view(url='http://sunlightlabs.github.io/openstates-api/legislators.html')),
    (r'^api/events/$', RedirectView.as_view(url='http://sunlightlabs.github.io/openstates-api/events.html')),
    (r'^api/districts/$', RedirectView.as_view(url='http://sunlightlabs.github.io/openstates-api/districts.html')),


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
