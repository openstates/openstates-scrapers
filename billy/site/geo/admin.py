from billy.site.geo.models import District

from django.contrib.gis import admin

admin.site.register(District, admin.GeoModelAdmin)
