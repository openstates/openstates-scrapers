#!/usr/bin/env python
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from votesmart import votesmart, VotesmartApiError
from fiftystates import settings

votesmart.apikey = settings.VOTESMART_API_KEY


class NYLegislatorScraper(LegislatorScraper):
    state = 'ny'

    def scrape(self, chamber, year):
        if chamber == 'upper':
            officeId = 9
        else:
            officeId = 7
        for cand in votesmart.officials.getByOfficeState(officeId, 'NY'):
            full_name = cand.firstName
            if cand.middleName:
                full_name += " " + cand.middleName
            full_name += " " + cand.lastName
            leg = Legislator('2009-2010', chamber, cand.officeDistrictName,
                             full_name, cand.firstName, cand.lastName,
                             cand.middleName, cand.officeParties)
            self.save_legislator(leg)
