import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee
from .utils import clean_committee_name, MDBMixin


class NJCommitteeScraper(CommitteeScraper, MDBMixin):
    jurisdiction = 'nj'

    def scrape(self, term, chambers):
        year_abr = term[0:4]

        self._init_mdb(year_abr)
        members_csv = self.access_to_csv('COMember')
        info_csv = self.access_to_csv('Committee')

        comm_dictionary = {}

        #Committe Info Database
        for rec in info_csv:
            abrv = rec["Code"]
            comm_name = rec["Description"]
            comm_type = rec["Type"]
            aide = rec["Aide"]
            contact_info = rec["Phone"]

            if abrv[0] == "A":
                chamber = "lower"
            elif abrv[0] == "S":
                chamber = "upper"

            comm = Committee(chamber, comm_name, comm_type = comm_type,
                             aide = aide, contact_info = contact_info)
            comm.add_source('http://www.njleg.state.nj.us/downloads.asp')
            comm_dictionary[abrv] = comm

        #Committee Member Database
        POSITIONS = {
            'C': 'chair',
            'V': 'vice-chair',
            '': 'member'
        }
        for member_rec in members_csv:
            # assignment=P means they are active, assignment=R means removed
            if member_rec['Assignment_to_Committee'] == 'P':
                abr = member_rec["Code"]
                comm_name = comm_dictionary[abr]

                leg = member_rec["Member"]
                role = POSITIONS[member_rec["Position_on_Committee"]]
                comm_name.add_member(leg, role=role)

                self.save_committee(comm_name)
