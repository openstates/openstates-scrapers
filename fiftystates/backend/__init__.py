from fiftystates import settings

import pymongo

conn = pymongo.Connection(getattr(settings, 'MONGO_HOST', 'localhost'),
                          getattr(settings, 'MONGO_PORT', 27017))

db = conn[getattr(settings, 'MONGO_DATABASE', 'fiftystates')]

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
