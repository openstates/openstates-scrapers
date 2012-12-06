import re
import urlparse
import htmlentitydefs

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from .utils import clean_committee_name, DBFMixin

import scrapelib
from dbfpy import dbf

class NJLegislatorScraper(LegislatorScraper, DBFMixin):
    jurisdiction = 'nj'

    def scrape(self, term, chambers):
        year_abr = term[0:4]

        file_url, db = self.get_dbf(year_abr, 'ROSTER')
        bio_url, bio_db = self.get_dbf(year_abr, 'LEGBIO')

        photos = {}
        for rec in bio_db:
            photos[rec['roster_key']] = rec['urlpicture']

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
                party = "Democratic"
            else:
                party = party
            chamber = rec["house"]
            if chamber == 'A':
                chamber = "lower"
            elif chamber == 'S':
                chamber = "upper"

            leg_status = rec["legstatus"]
            # skip Deceased/Retired members
            if leg_status != 'Active':
                continue
            title = rec["title"]
            legal_position = rec["legpos"]
            address = rec["address"]
            city = rec["city"]
            state = rec["state"]
            zipcode = rec["zipcode"]
            phone = rec["phone"]
            if 'email' in rec:
                email = rec["email"]
            else:
                email = ''
            photo_url = photos[rec['roster_key']]
            url = ('http://www.njleg.state.nj.us/members/bio.asp?Leg=' +
                   str(int(rec['roster_key'])))
            address = '{0}\n{1}, {2} {3}'.format(rec['address'], rec['city'],
                                                 rec['state'], rec['zipcode'])
            gender = {'M': 'Male', 'F': 'Female'}[rec['sex']]

            leg = Legislator(term, chamber, str(district), full_name,
                             first_name, last_name, middle_name, party,
                             suffixes=suffix, title=title,
                             legal_position=legal_position,
                             email=email, url=url, photo_url=photo_url,
                             gender=gender)
            leg.add_source(url)
            leg.add_source(file_url)
            leg.add_office('district', 'District Office', address=address,
                           phone=rec['phone'])
            self.save_legislator(leg)
