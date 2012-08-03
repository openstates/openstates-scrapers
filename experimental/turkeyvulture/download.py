import os
import sys
import requests
from billy.models import db


def main(abbr, session=None):
    try:
        os.makedirs('billtext/%s' % abbr)
    except OSError:
        pass
    spec = {'state': abbr}
    if session is not None:
        spec.update(session=session)
    for bill in db.bills.find(spec):
        with open('billtext/%s/%s' % (abbr, bill['_id']), 'w') as f:
            try:
                url = bill['versions'][0]['url']
                print 'trying', url
                resp = requests.get(url)
            except KeyboardInterrupt:
                import pdb;pdb.set_trace()
            except Exception as e:
                print 'failed with', e
                pass
            f.write(resp.text.encode(resp.encoding))

if __name__ == '__main__':
    import sys
    if 2 < len(sys.argv):
        session = sys.argv[2]
    else:
        session = None
    main(sys.argv[1], session)