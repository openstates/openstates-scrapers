from billy.core import settings

# mongodb
MONGO_HOST = getattr(settings, 'OYSTER_MONGO_HOST', settings.MONGO_HOST)
MONGO_PORT = getattr(settings, 'OYSTER_MONGO_PORT', settings.MONGO_PORT)
MONGO_DATABASE = 'oyster'
MONGO_LOG_MAXSIZE = 100000000

# scrapelib
USER_AGENT = 'oyster'
REQUESTS_PER_MINUTE = 180
REQUEST_TIMEOUT = 300

# other
CELERY_TASK_MODULES = ['oyster.ext.superfastmatch', 'oyster.ext.elasticsearch']
RETRY_ATTEMPTS = 3
RETRY_WAIT_MINUTES = 60

DEFAULT_STORAGE_ENGINE = 's3'
AWS_KEY = getattr(settings, 'AWS_KEY', None)
AWS_SECRET = getattr(settings, 'AWS_SECRET', None)
AWS_BUCKET = getattr(settings, 'AWS_BUCKET', None)
AWS_PREFIX = 'documents/'

ELASTICSEARCH_HOST = getattr(settings, 'ELASTICSEARCH_HOST', None)
ELASTICSEARCH_INDEX = 'bills'
ELASTICSEARCH_DOC_TYPE = 'version'

SUPERFASTMATCH_URL = 'http://ec2-107-20-40-130.compute-1.amazonaws.com/'


states = ('ak', 'al', 'ar', 'az', 'ca', 'co', 'ct', 'dc', 'de', 'fl', 'ga',
  'hi', 'ia', 'id', 'il', 'in', 'ks', 'ky', 'la', 'ma', 'md', 'me', 'mi', 'mn',
  'mo', 'ms', 'mt', 'nc', 'nd', 'ne', 'nh', 'nj', 'nm', 'nv', 'ny', 'oh', 'ok',
  'or', 'pa', 'pr', 'ri', 'sc', 'sd', 'tn', 'tx', 'ut', 'va', 'vt', 'wa', 'wi',
  'wv', 'wy')

def SUPERFASTMATCH_ID_FUNC(doc_id):
    doctype, docid = doc_id.split('D')
    doctype = states.index(doctype.lower())
    docid = int(docid)
    return doctype, docid


# this is ridiculous
DOCUMENT_CLASSES = {}

for state in states:
    try:
        DOCUMENT_CLASSES[state+':billtext'] = __import__('openstates.'+ state, fromlist=['document_class']).document_class
    except ImportError:
        pass

