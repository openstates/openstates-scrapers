import os

MONGO_HOST = os.environ.get('OPENSTATES_MONGO_HOST', 'localhost')
MONGO_PORT = os.environ.get('OPENSTATES_MONGO_PORT', 27017)
MONGO_DATABASE = os.environ.get('OPENSTATES_MONGO_DATABASE', 'fiftystates')

BILLY_DATA_DIR = os.path.abspath(os.path.join(os.path.abspath(
            os.path.dirname(__file__)), '../../data'))

# Set to None to disable caching
BILLY_CACHE_DIR = os.path.abspath(os.path.join(os.path.abspath(
            os.path.dirname(__file__)), '../../cache'))

BILLY_ERROR_DIR = os.path.abspath(os.path.join(os.path.abspath(
            os.path.dirname(__file__)), '../../errors'))

SCRAPELIB_TIMEOUT = 600
SCRAPELIB_RETRY_ATTEMPTS = 3
SCRAPELIB_RETRY_WAIT_SECONDS = 20

NIMSP_API_KEY = ''
VOTESMART_API_KEY = ''
SUNLIGHT_SERVICES_KEY = ''

try:
    from billy_settings import *
except ImportError:
    pass
