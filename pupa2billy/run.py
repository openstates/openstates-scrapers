from __future__ import print_function
import os
import sys
import shutil
import importlib
from .legislators import PupaLegislatorScraper
from .committees import PupaCommitteeScraper
from .bills import PupaBillScraper
from .votes import PupaVoteScraper
from .events import PupaEventScraper
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
    os.makedirs(os.path.join(juris_dir, 'committees'))
    os.makedirs(os.path.join(juris_dir, 'bills'))
    os.makedirs(os.path.join(juris_dir, 'votes'))
    os.makedirs(os.path.join(juris_dir, 'events'))

    ls = PupaLegislatorScraper(metadata, juris_dir, jurisdiction=jurisdiction)
    ls.scrape()

    cs = PupaCommitteeScraper(metadata, juris_dir, jurisdiction=jurisdiction)
    cs.scrape()

    bs = PupaBillScraper(metadata, juris_dir, jurisdiction=jurisdiction)
    bs.scrape()

    vs = PupaVoteScraper(metadata, juris_dir, jurisdiction=jurisdiction)
    vs.scrape()

    es = PupaEventScraper(metadata, juris_dir, jurisdiction=jurisdiction)
    es.scrape()
