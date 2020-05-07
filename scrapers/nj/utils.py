import os
import re
import csv
import zipfile
import subprocess


def clean_committee_name(comm_name):
    comm_name = comm_name.strip()
    comm_name = re.sub(" ?[-,] (Co|Vice)?[- ]?Chair$", "", comm_name)
    comm_name = re.sub("Appropriations - S/C:", "Appropriations-S/C on", comm_name)
    if comm_name == "Appropriations-S/C Stimulus":
        comm_name = "Appropriations-S/C on Stimulus"

    return comm_name


def chamber_name(chamber):
    if chamber == "upper":
        return "senate"
    else:
        return "assembly"


class MDBMixin(object):
    def _init_mdb(self, year):
        if year < 2018:
            self.mdbfile = "DB%s.mdb" % year
            url = "ftp://www.njleg.state.nj.us/ag/%sdata/DB%s.zip" % (year, year)
            fname, resp = self.urlretrieve(url)
            zf = zipfile.ZipFile(fname)
            zf.extract(self.mdbfile)
            os.remove(fname)
        else:
            url = "ftp://www.njleg.state.nj.us/ag/%sdata/DB%s.mdb" % (year, year)
            fname, resp = self.urlretrieve(url)
            self.mdbfile = fname
            self.info("mdb filename = " + fname)

    # stolen from nm/bills.py
    def access_to_csv(self, table):
        """ using mdbtools, read access tables as CSV """
        commands = ["mdb-export", self.mdbfile, table]
        pipe = subprocess.Popen(commands, stdout=subprocess.PIPE, close_fds=True).stdout
        csvfile = csv.DictReader(line.decode() for line in pipe)
        return csvfile
