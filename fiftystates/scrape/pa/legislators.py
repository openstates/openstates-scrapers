import re

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.pa import metadata
from fiftystates.scrape.pa.utils import legislators_url

from BeautifulSoup import BeautifulSoup


class PALegislatorScraper(LegislatorScraper):
    state = 'pa'

    def scrape(self, chamber, year):
        # Pennsylvania doesn't make member lists easily available
        # for previous sessions, unfortunately
        if int(year) < 2009:
            #raise NoDataForPeriod(year)
            return

        session = "%s-%d" % (year, int(year) + 1)
        leg_list_url = legislators_url(chamber)

        with self.urlopen(leg_list_url) as member_list_page:
            member_list_page = BeautifulSoup(member_list_page)
            for link in member_list_page.findAll(
                'a', href=re.compile('_bio\.cfm\?id=')):

                full_name = link.contents[0][0:-4]
                last_name = full_name.split(',')[0]
                first_name = full_name.split(' ')[1]

                if len(full_name.split(' ')) > 2:
                    middle_name = full_name.split(' ')[2].strip(',')
                else:
                    middle_name = ''

                party = link.contents[0][-2]
                if party == 'R':
                    party = "Republican"
                elif party == 'D':
                    party = "Democrat"

                district = re.search(
                    "District (\d+)", link.parent.contents[1]).group(1)

                legislator = Legislator(session, chamber, district,
                                        full_name, first_name, last_name,
                                        middle_name, party)
                legislator.add_source(leg_list_url)
                self.save_legislator(legislator)

