import re
from dbfpy import dbf


def clean_committee_name(comm_name):
    comm_name = comm_name.strip()
    comm_name = re.sub(' ?[-,] (Co|Vice)?[- ]?Chair$', '', comm_name)
    comm_name = re.sub('Appropriations - S/C:', 'Appropriations-S/C on',
                       comm_name)
    if comm_name == 'Appropriations-S/C Stimulus':
        comm_name = 'Appropriations-S/C on Stimulus'

    return comm_name


def parse_ftp_listing(text):
    lines = text.strip().split('\r\n')
    return (' '.join(line.split()[3:]) for line in lines)


def chamber_name(chamber):
    if chamber == 'upper':
        return 'senate'
    else:
        return 'assembly'

class DBFMixin(object):
    def get_dbf(self, year, name):
        url = 'ftp://www.njleg.state.nj.us/ag/%sdata/%s.DBF' % (year, name)
        dbf_file, resp = self.urlretrieve(url)
        db = dbf.Dbf(dbf_file)
        return url, db
