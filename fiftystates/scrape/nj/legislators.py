import re
import urlparse
import htmlentitydefs

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.nj.utils import clean_committee_name

import scrapelib
from dbfpy import dbf

class NJLegislatorScraper(LegislatorScraper):
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
            self.scrape_legislators(year_abr, session, term_name)
        elif chamber == 'lower':
            self.scrape_legislators(year_abr, session, term_name)

    def scrape_legislators(self, year_abr, session, term_name):

        file_url = 'ftp://www.njleg.state.nj.us/ag/%sdata/ROSTER.DBF' % (year_abr)

        ROSTER_dbf, resp = self.urlretrieve(file_url)
        db = dbf.Dbf(ROSTER_dbf)        

        for rec in db:
            first_name = rec["firstname"]
            middle_name = rec["midname"]
            last_name = rec["lastname"]
            suffix = rec["suffix"]
            full_name = first_name + " " + middle_name + " " + last_name + " " + suffix
            full_name = full_name.replace('  ', ' ')
            full_name = full_name[0: len(full_name) - 1]
            
            district = int(rec["district"])
            party = rec["party"]
            if party == 'R':
                party = "Republican"
            elif party == 'D':
                party = "Democrat"
            else:
                party = party
            chamber = rec["house"]
            if chamber == 'A':
                chamber = "lower"
            elif chamber == 'S':
                chamber = "upper"

            title = rec["title"]
            legal_position = rec["legpos"]
            leg_status = rec["legstatus"]
            address = rec["address"]
            city = rec["city"]
            state = rec["state"]
            zipcode = rec["zipcode"]
            phone = rec["phone"]

            leg = Legislator(term_name, chamber, str(district), full_name, first_name, last_name, middle_name, party, title = title, legal_position = legal_position, leg_status = leg_status, address = address, city = city, state = state, zipcode = zipcode, phone = phone)
            leg.add_source(file_url)
            self.save_legislator(leg)
