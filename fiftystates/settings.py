import os

MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_DATABASE = 'fiftystates'

FIFTYSTATES_DATA_DIR = os.path.abspath(os.path.join(os.path.abspath(
            os.path.dirname(__file__)), '..', 'data'))

# Set to None to disable caching
FIFTYSTATES_CACHE_DIR = os.path.abspath(os.path.join(os.path.abspath(
            os.path.dirname(__file__)), '..', 'cache'))

FIFTYSTATES_ERROR_DIR = os.path.abspath(os.path.join(os.path.abspath(
            os.path.dirname(__file__)), '..', 'errors'))

NIMSP_API_KEY = ''
VOTESMART_API_KEY = ''
