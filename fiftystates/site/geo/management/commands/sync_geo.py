import os
import sys
import urllib2
import zipfile
from cStringIO import StringIO

from fiftystates.site.geo.models import (District, state_nums,
                                         upper_district_mapping,
                                         lower_district_mapping)

from django.contrib.gis.utils import LayerMapping
from django.core.management.base import BaseCommand

# Unprojected NAD83
# +proj=longlat +ellps=GRS80 +datum=NAD83 +no_defs
SOURCE_SRS = 4269


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            abbrev = args[0].lower()
        except IndexError:
            print "Please provide a state to import"
            sys.exit(1)

        num = None
        for n, s in state_nums.iteritems():
            if s == abbrev:
                num = n
                break
        if num is None:
            print "Could not find census state number for %s" % args[0]
            sys.exit(1)

        for chamber, mapping in {'su': upper_district_mapping,
                                 'sl': lower_district_mapping}.items():
            path = os.path.abspath(os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(
                                __file__))), 'data/'))

            path = os.path.join(path, "%s%s_d11.shp" % (chamber, num))

            try:
                LayerMapping(District, path, mapping,
                             source_srs=SOURCE_SRS,
                             transform=True).save(strict=True)
            except:
                self.download_state_shapefiles(path, num)
                LayerMapping(District, path, mapping,
                             source_srs=SOURCE_SRS,
                             transform=True).save(strict=True)

    def download_state_shapefiles(self, path, num):
        for chamber in ('su', 'sl'):
            print "Downloading %s%s_d11_shp.zip" % (chamber, num)

            data = urllib2.urlopen(
                "http://www.census.gov/geo/cob/bdy/"
                "%s/%s06shp/%s%s_d11_shp.zip" % (chamber, chamber,
                                                 chamber, num))

            data = StringIO(data.read())
            zip = zipfile.ZipFile(data)
            zip.extractall(os.path.dirname(path))
