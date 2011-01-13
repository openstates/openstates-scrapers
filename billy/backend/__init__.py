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

__metadata = {}


def metadata(state):
    """
    Grab the metadata for the given state (two-letter abbreviation).
    """
    # This data should change very rarely and is queried very often so
    # cache it here
    state = state.lower()
    if state in __metadata:
        return __metadata[state]
    return db.metadata.find_one({'_id': state})
