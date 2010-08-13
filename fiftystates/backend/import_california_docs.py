from fiftystates.backend import db
from fiftystates.scrape.ca.models import CABillVersion

from sqlalchemy.orm import sessionmaker, relation, backref
from sqlalchemy import create_engine

import gridfs
from pymongo.son import SON


def import_docs(user='', pw='', host='localhost', db='capublic'):
    if user and pw:
        conn_str = 'mysql://%s:%s@' % (user, pw)
    else:
        conn_str = 'mysql://'

    conn_str = '%s%s/%s?charset=utf8&unix_socket=/tmp/mysql.sock' % (
        conn_str, host, db)
    engine = create_engine(conn_str)
    Session = sessionmaker(bind=engine)
    session = Session()

    fs = gridfs.GridFS(db, collection="documents")

    for version in session.query(CABillVersion):
        if fs.exists({"metadata": {"ca_version_id": version.bill_version_id}}):
            continue

        query = SON([('_id', 'ca')])
        update = SON([('$inc', SON([('seq', 1)]))])
        seq = db.command(SON([('findandmodify': 'doc_ids'),
                              ('query', query),
                              ('update', update),
                              ('new', True),
                              ('upsert', True)]))['value']['seq']

        doc_id = "%s%08d" % seq
        print "Saving: %s" % doc_id

        fs.put(version.bill_xml, _id=doc_id,
               metadata={"ca_version_id": version.bill_version_id})

if __name__ == '__main__':
    import_docs()
