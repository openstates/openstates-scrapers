import datetime

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.committees import CommitteeScraper, Committee
from fiftystates.scrape.nv.utils import clean_committee_name

import lxml.etree
from dbfpy import dbf

class NJCommitteeScraper(CommitteeScraper):
    state = 'nj'

    def scrape(self, chamber, year):
        self.save_errors=False

        if year < 1996:
            raise NoDataForYear(year)
        elif year == 1996:
            year_abr = 9697
        elif year == 1998:
            year_abr = 9899
        else:
            year_abr = year

        session = (int(year) - 2010) + 214

        if chamber == 'upper':
            self.scrape_committees(year_abr, session)
        elif chamber == 'lower':
            self.scrape_committees(year_abr, session)

    def scrape_committees(self, year_abr, session):

        members_url = 'ftp://www.njleg.state.nj.us/ag/%sdata/COMEMB.DBF' % (year_abr)
        comm_info__url = 'ftp://www.njleg.state.nj.us/ag/%sdata/COMMITT.DBF' % (year_abr)

        members_db = dbf.Dbf("COMEMB.DBF")
        info_db = dbf.Dbf("COMMITT.DBF")

        comm_dictionary = {}

        for name_rec in info_db:
            abr = name_rec["code"]
            comm_name = name_rec["descriptio"]

            comm_dictionary[abr] = comm_name

        for member_rec in members_db:
            abrv = member_rec["code"]
            comm_name = comm_dictionary[abrv]
            
            if abrv[0] == "A":
                chamber = "General Assembly"
            elif abrv[0] == "S":
                chamber = "Senate"
            leg = member_rec["member"]            
            comm = Committee(chamber, comm_name)
            comm.add_member(leg)
            self.save_committee(comm) 
