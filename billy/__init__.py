__import__('pkg_resources').declare_namespace(__name__)

import os

from billy.conf import settings

class LazyDb(object):

    def __init__(self):
        self._db = None

    def __getattr__(self, attr):

        if not self._db:
            import pymongo

            host = settings.MONGO_HOST
            port = settings.MONGO_PORT
            db_name = settings.MONGO_DATABASE

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
