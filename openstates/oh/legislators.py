import re

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class OHLegislatorScraper(LegislatorScraper):
    state = 'oh'

    def scrape(self, chamber, term):
        if term != '2011-2012':
            raise NoDataForPeriod(term)

        if chamber == 'upper':
            self.scrape_senators(chamber, term)
        else:
            self.scrape_reps(chamber, term)

    def scrape_reps(self, chamber, term):
        # There are 99 House districts
        for district in xrange(1, 100):
            rep_url = ('http://www.house.state.oh.us/components/'
                       'com_displaymembers/page.php?district=%d' % district)

            with self.urlopen(rep_url) as page:
                page = lxml.html.fromstring(page)

                for el in page.xpath('//table[@class="page"]'):
                    rep_link = el.xpath('tr/td/title')[0]
                    full_name = rep_link.text
                    party = full_name[-2]
                    full_name = full_name[0:-3]

                    if party == "D":
                        party = "Democratic"
                    elif party == "R":
                        party = "Republican"

                    leg = Legislator(term, chamber, str(district),
                                     full_name, party=party, url=url)
                    leg.add_source(rep_url)

                self.save_legislator(leg)

    def scrape_senators(self, chamber, term):
        url = 'http://www.ohiosenate.gov/directory.html'
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for el in page.xpath('//table[@class="fullWidth"]/tr/td'):
                sen_link = el.xpath('a[@class="senatorLN"]')[1]
                sen_url = el.get('href')

                full_name = sen_link.text
                full_name = full_name[0:-2]
                if full_name == 'To Be Announced':
                    continue

                district = el.xpath('string(h3)').split()[1]

                party = el.xpath('string(a[@class="senatorLN"]/span)')

                if party == "D":
                    party = "Democratic"
                elif party == "R":
                    party = "Republican"

                office_phone = el.xpath("b[text() = 'Phone']")[0].tail
                office_phone = office_phone.strip(' :')

                photo_url = el.xpath("a/img")[0].attrib['src']
                email = el.xpath('.//span[@class="tan"]/text()')[1]

                leg = Legislator(term, chamber, district, full_name,
                                 party=party, photo_url=photo_url, url=sen_url,
                                 office_phone=office_phone, email=email)
                leg.add_source(url)

                self.save_legislator(leg)
