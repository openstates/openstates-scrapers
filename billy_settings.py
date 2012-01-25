import os

from os.path import abspath, dirname, join

PROJECT_DIR = abspath(dirname(__file__)) 
DATA_DIR = join(PROJECT_DIR, 'data')

SCRAPER_PATHS=[os.path.join(os.getcwd(), 'openstates')]
MONGO_HOST = os.environ.get('OPENSTATES_MONGO_HOST', 'localhost')
MONGO_PORT = os.environ.get('OPENSTATES_MONGO_PORT', 27017)
MONGO_DATABASE = os.environ.get('OPENSTATES_MONGO_DATABASE', 'fiftystates')


try:
    from billy_local import *
except ImportError:
    pass
