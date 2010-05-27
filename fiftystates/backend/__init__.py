from fiftystates import settings

import pymongo

conn = pymongo.Connection(getattr(settings, 'MONGO_HOST', 'localhost'),
                          getattr(settings, 'MONGO_PORT', 27017))

db = conn[getattr(settings, 'MONGO_DATABASE', 'fiftystates')]
