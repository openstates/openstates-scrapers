import os
import csv

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
from lxml.etree import ElementTree


class MTLegislatorScraper(LegislatorScraper):
    state = 'mt'

    def __init__(self, *args, **kwargs):
        super(MTLegislatorScraper, self).__init__(*args, **kwargs)

    def scrape(self, chamber, term):
        for tdata in self.metadata['terms']:
            if term == tdata['name']:
                year = tdata['start_year']
                break

        url = 'http://leg.mt.gov/content/sessions/%s/%d%sMembers.txt' % \
            (term, year, chamber == 'upper' and 'Senate' or 'House')

        file = self.urlopen(url)
        file = file.replace('"""', '"') # weird triple quotes
        file = file.split(os.linesep)

        csv_parser = csv.reader(file)

        for entry in csv_parser:
            if not entry:
                continue
            last_name = entry[0]
            first_name = entry[1]
            party_letter = entry[2]
            district = entry[3]#.split('D ')[1]
            if party_letter == '(R)':
                party = 'Republican'
            elif party_letter == '(D)':
                party = 'Democratic'
            else:
                party = party_letter
            first_name = first_name.capitalize()
            last_name = last_name.capitalize()
            #All we care about is the number
            district = district.split(' ')[1]

            legislator = Legislator(term, chamber, district, '%s %s' % (first_name, last_name), \
                                    first_name, last_name, '', party)
            legislator.add_source(url)
            self.save_legislator(legislator)
