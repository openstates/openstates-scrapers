'''
Build an index for each state (er, territory/place/region/shapefile)
in mongo.
'''
from subprocess import check_call
from billy import db

from .build_index import build_index

def main():
    for abbr in db.metadata.distinct('_id'):
        check_call('')

if __name__ == '__main__':
    main()