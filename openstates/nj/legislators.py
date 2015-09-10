import re
import urlparse
import htmlentitydefs

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from .utils import clean_committee_name, MDBMixin

import scrapelib

class NJLegislatorScraper(LegislatorScraper, MDBMixin):
    jurisdiction = 'nj'

    def scrape(self, term, chambers):
        year_abr = term[0:4]

        self._init_mdb(year_abr)

        roster_csv = self.access_to_csv('Roster')
        bio_csv = self.access_to_csv('LegBio')

        photos = {}
        for rec in bio_csv:
            photos[rec['Roster Key']] = rec['URLPicture']

        for rec in roster_csv:
            first_name = rec["Firstname"]
            middle_name = rec["MidName"]
            last_name = rec["LastName"]
            suffix = rec["Suffix"]
            full_name = first_name + " " + middle_name + " " + last_name + " " + suffix
            full_name = full_name.replace('  ', ' ')
            full_name = full_name[0: len(full_name) - 1]

            district = int(rec["District"])
            party = rec["Party"]
            if party == 'R':
                party = "Republican"
            elif party == 'D':
                party = "Democratic"
            else:
                party = party
            chamber = rec["House"]
            if chamber == 'A':
                chamber = "lower"
            elif chamber == 'S':
                chamber = "upper"

            leg_status = rec["LegStatus"]
            # skip Deceased/Retired members
            if leg_status != 'Active':
                continue
            title = rec["Title"]
            legal_position = rec["LegPos"]
            phone = rec["Phone"] or None
            email = None
            if rec["Email"]:
                email = rec["Email"]
            try:
                photo_url = photos[rec['Roster Key']]
            except KeyError:
                photo_url = ''
                self.warning('no photo url for %s', rec['Roster Key'])
            url = ('http://www.njleg.state.nj.us/members/bio.asp?Leg=' +
                   str(int(rec['Roster Key'])))
            address = '{0}\n{1}, {2} {3}'.format(rec['Address'], rec['City'],
                                                 rec['State'], rec['Zipcode'])
            gender = {'M': 'Male', 'F': 'Female'}[rec['Sex']]

            leg = Legislator(term, chamber, str(district), full_name,
                             first_name, last_name, middle_name, party,
                             suffixes=suffix, title=title,
                             legal_position=legal_position,
                             url=url, photo_url=photo_url,
                             gender=gender)
            leg.add_office('district', 'District Office', address=address,
                           phone=phone, email=email)
            leg.add_source(url)
            leg.add_source('http://www.njleg.state.nj.us/downloads.asp')
            self.save_legislator(leg)
