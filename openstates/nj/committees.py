import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee
from openstates.nv.utils import clean_committee_name

import lxml.etree
from dbfpy import dbf
import scrapelib

class NJCommitteeScraper(CommitteeScraper):
    state = 'nj'

    def scrape(self, chamber, term_name):
        self.save_errors=False

        year = int(term_name[0:4])
        if year < 2000:
            raise NoDataForPeriod(term_name)
        else:
            year_abr = year
        session = ((int(year) - 2010)/2) + 214

        if chamber == 'upper':
            self.scrape_committees(year_abr, session)
        elif chamber == 'lower':
            self.scrape_committees(year_abr, session)

    def scrape_committees(self, year_abr, session):

        members_url = 'ftp://www.njleg.state.nj.us/ag/%sdata/COMEMB.DBF' % (year_abr)
        comm_info_url = 'ftp://www.njleg.state.nj.us/ag/%sdata/COMMITT.DBF' % (year_abr)
     
        COMEMB_dbf, resp = self.urlretrieve(members_url)
        COMMIT_dbf, resp2 = self.urlretrieve(comm_info_url)

        members_db = dbf.Dbf(COMEMB_dbf)
        info_db = dbf.Dbf(COMMIT_dbf)

        comm_dictionary = {}

        #Committe Info Database
        for name_rec in info_db:
            abrv = name_rec["code"]
            comm_name = name_rec["descriptio"]
            comm_type = name_rec["type"]
            aide = name_rec["aide"]
            contact_info = name_rec["phone"]

            if abrv[0] == "A":
                chamber = "upper"
            elif abrv[0] == "S":
                chamber = "lower"

            comm = Committee(chamber, comm_name, comm_type = comm_type, aide = aide, contact_info = contact_info)
            comm.add_source(members_url)
            comm.add_source(comm_info_url)
            comm_dictionary[abrv] = comm

        #Committee Member Database
        for member_rec in members_db:
            abr = member_rec["code"]
            comm_name = comm_dictionary[abr]
            
            leg = member_rec["member"]            
            comm_name.add_member(leg)
            
            self.save_committee(comm_name) 
