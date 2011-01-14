__import__('pkg_resources').declare_namespace(__name__)

import os

from billy import settings

import pymongo
import gridfs

host = os.environ.get('OPENSTATES_MONGO_HOST',
                      getattr(settings, 'MONGO_HOST', 'localhost'))
port = int(os.environ.get('OPENSTATES_MONGO_PORT',
                      getattr(settings, 'MONGO_PORT', 27017)))
db_name = os.environ.get('OPENSTATES_MONGO_DATABASE',
                         getattr(settings, 'MONGO_DATABASE',
                                 'fiftystates'))

conn = pymongo.Connection(host, port)
db = conn[db_name]

fs = gridfs.GridFS(db, collection="documents")
