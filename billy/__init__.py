__import__('pkg_resources').declare_namespace(__name__)

import os

from billy import settings

class LazyDb(object):

    def __init__(self):
        self._db = None

    def __getattr__(self, attr):

        if not self._db:
            import pymongo

            host = os.environ.get('OPENSTATES_MONGO_HOST',
                                  getattr(settings, 'MONGO_HOST', 'localhost'))
            port = int(os.environ.get('OPENSTATES_MONGO_PORT',
                                  getattr(settings, 'MONGO_PORT', 27017)))
            db_name = os.environ.get('OPENSTATES_MONGO_DATABASE',
                                     getattr(settings, 'MONGO_DATABASE',
                                             'fiftystates'))

            conn = pymongo.Connection(host, port)
            self._db = conn[db_name]

        return getattr(self._db, attr)

class LazyFs():

    def __init__(self):
        self._fs = None

    def __getattr__(self, attr):
        import gridfs

        if not self._fs:
            self._fs = gridfs.GridFS(db._db, collection="documents")


db = LazyDb()
fs = LazyFs()
