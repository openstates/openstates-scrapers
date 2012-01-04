import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee
from .utils import clean_committee_name, DBFMixin

import lxml.etree
from dbfpy import dbf
import scrapelib

class NJCommitteeScraper(CommitteeScraper, DBFMixin):
    state = 'nj'

    def scrape(self, chamber, term):
        year = term[0:4]
        if chamber == 'upper':
            self.scrape_committees(year)
        elif chamber == 'lower':
            self.scrape_committees(year)

    def scrape_committees(self, year_abr):

        members_url, members_db = self.get_dbf(year_abr, 'COMEMB')
        comm_info_url, info_db = self.get_dbf(year_abr, 'COMMITT')

        comm_dictionary = {}

        #Committe Info Database
        for name_rec in info_db:
            abrv = name_rec["code"]
            comm_name = name_rec["descriptio"]
            comm_type = name_rec["type"]
            aide = name_rec["aide"]
            contact_info = name_rec["phone"]

            if abrv[0] == "A":
                chamber = "lower"
            elif abrv[0] == "S":
                chamber = "upper"

            comm = Committee(chamber, comm_name, comm_type = comm_type,
                             aide = aide, contact_info = contact_info)
            comm.add_source(members_url)
            comm.add_source(comm_info_url)
            comm_dictionary[abrv] = comm

        #Committee Member Database
        for member_rec in members_db:
            # assignment=P means they are active, assignment=R means removed
            if member_rec['assignment'] == 'P':
                abr = member_rec["code"]
                comm_name = comm_dictionary[abr]

                leg = member_rec["member"]
                comm_name.add_member(leg)

                self.save_committee(comm_name)
