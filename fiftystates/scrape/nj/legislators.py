import re
import urlparse
import htmlentitydefs

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.nj.utils import clean_committee_name

import urllib
from dbfpy import dbf

class NJLegislatorScraper(LegislatorScraper):
    state = 'nj'

    def scrape(self, chamber, year):
        self.save_errors=False

        if year < 1996:
            raise NoDataForPeriod(year)
        elif year == 1996:
            year_abr = 9697
        elif year == 1998:
            year_abr = 9899
        else:
            year_abr = year

        session = (int(year) - 2010) + 214

        if chamber == 'upper':
            self.scrape_legislators(year_abr, session)
        elif chamber == 'lower':
            self.scrape_legislators(year_abr, session)

    def scrape_legislators(self, year_abr, session):

        file_url = 'ftp://www.njleg.state.nj.us/ag/%sdata/ROSTER.MDX' % (year_abr)

        db = dbf.Dbf("ROSTER.DBF")        
        for rec in db:
            first_name = rec["firstname"]
            middle_name = rec["midname"]
            last_name = rec["lastname"]
            suffix = rec["suffix"]
            full_name = first_name + " " + middle_name + " " + last_name + " " + suffix
            full_name = full_name.replace('  ', ' ')
            full_name = full_name[0: len(full_name) - 1]
            
            district = rec["district"]
            district = int(district)
            party = rec["party"]
            if party == 'R':
                party = "Republican"
            elif party == 'D':
                party = "Democracy"
            else:
                party = party
            chamber = rec["house"]
            if chamber == 'A':
                chamber = "General Assembly"
            elif chamber == 'S':
                chamber = "Senate"

            title = rec["title"]
            legal_position = rec["legpos"]
            leg_status = rec["legstatus"]
            address = rec["address"]
            city = rec["city"]
            state = rec["state"]
            zipcode = rec["zipcode"]
            phone = rec["phone"]

            leg = Legislator(session, chamber, district, full_name, first_name, last_name, middle_name, party, title = title, legal_position = legal_position, leg_status = leg_status, address = address, city = city, state = state, zipcode = zipcode, phone = phone)
            leg.add_source(file_url)
            self.save_legislator(leg)
