import os
import sys
import urllib2
import zipfile
from cStringIO import StringIO

from billy.site.geo.models import (District, state_nums,
                                         upper_district_mapping,
                                         lower_district_mapping)

from django.contrib.gis.utils import LayerMapping
from django.core.management.base import BaseCommand

# Unprojected NAD83
# +proj=longlat +ellps=GRS80 +datum=NAD83 +no_defs
SOURCE_SRS = 4269


class Command(BaseCommand):
    def handle(self, *args, **options):
        if len(args):
            for arg in args:
                abbrev = arg.lower()
                num = None
                for n, s in state_nums.iteritems():
                    if s == abbrev:
                        num = n
                        break
                if num is None:
                    print "Could not find census state number for %s" % args[0]
                    sys.exit(1)

                import_state(num)
        else:
            print "Importing All States..."
            for n in state_nums:
                print state_nums[n]
                self.import_state(n)
            sys.exit(0)

    def import_state(self, num):
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
                try:
                    self.download_state_shapefiles(path, num)
                    LayerMapping(District, path, mapping,
                                 source_srs=SOURCE_SRS,
                                 transform=True).save(strict=True)
                except:
                    print 'error importing %s' % path

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
