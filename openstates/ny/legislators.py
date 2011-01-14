#!/usr/bin/env python
from billy.scrape.legislators import LegislatorScraper, Legislator
from votesmart import votesmart, VotesmartApiError
from billy import settings
import os

from nyss_billyslation.models import senators

votesmart.apikey = os.environ.get('VOTESMART_API_KEY', settings.VOTESMART_API_KEY)


class NYLegislatorScraper(LegislatorScraper):
    state = 'ny'

    def scrape(self, chamber, year):
        if chamber == 'upper':
            self.scrape_senators()
        else:
            for cand in votesmart.officials.getByOfficeState(7, 'NY'):
                full_name = cand.firstName
                if cand.middleName:
                    full_name += " " + cand.middleName
                full_name += " " + cand.lastName
                leg = Legislator('2009-2010', chamber, cand.officeDistrictName,
                                 full_name, cand.firstName, cand.lastName,
                                 cand.middleName, cand.officeParties)
                self.save_legislator(leg)

    def scrape_senators(self):
        for sen in senators.legislators.values():
            leg = Legislator('2009-2010', 'upper', sen['district'],
                             sen['fullname'],
                             party=','.join(sen['parties']))
            self.save_legislator(leg)
