__import__('pkg_resources').declare_namespace(__name__)

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

db = LazyDb()
