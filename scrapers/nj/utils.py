import io
import re
import csv
import zipfile


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
        url = (
            f"https://www.njleg.state.nj.us/leg-databases/{year}data/DB{year}_TEXT.zip"
        )
        fname, resp = self.urlretrieve(url)
        self.zipfile = zipfile.ZipFile(fname)

    def to_csv(self, table):
        buf = io.StringIO(self.zipfile.read(table).decode("cp1252"))
        csvfile = csv.DictReader(buf)
        return csvfile
