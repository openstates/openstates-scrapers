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

NIMSP_API_KEY = '33b067cfce326567afd9e60d78a9ef6e'
VOTESMART_API_KEY = '27d0492dd79ef95c882a1dacad4d960e'
