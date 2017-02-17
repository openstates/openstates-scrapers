from __future__ import print_function
import os
import sys
import shutil
import importlib
from .legislators import PupaLegislatorScraper
from .bills import PupaBillScraper
from .settings import BILLY_DATA_DIR


if __name__ == '__main__':
    jurisdiction = sys.argv[1]
    mod = importlib.import_module(jurisdiction)
    metadata = mod.metadata

    try:
        shutil.rmtree(BILLY_DATA_DIR)
    except OSError:
        pass

    juris_dir = os.path.join(BILLY_DATA_DIR, jurisdiction)
    os.makedirs(os.path.join(juris_dir, 'legislators'))
    os.makedirs(os.path.join(juris_dir, 'bills'))

    ls = PupaLegislatorScraper(metadata, juris_dir, jurisdiction=jurisdiction)
    ls.scrape()

    bs = PupaBillScraper(metadata, juris_dir, jurisdiction=jurisdiction)
    bs.scrape()
