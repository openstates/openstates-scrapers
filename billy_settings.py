import os

from os.path import abspath, dirname, join

SCRAPER_PATHS=[os.path.join(os.getcwd(), 'openstates')]
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_DATABASE = 'fiftystates'

try:
    from billy_local import *
except ImportError:
    pass
