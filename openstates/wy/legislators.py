from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
class WYLegislatorScraper(LegislatorScraper):
    state = 'wy'

    urls = {
            'old': 'http://legisweb.state.wy.us/%s/members/%s.htm',
            'new': 'http://legisweb.state.wy.us/LegbyYear/LegislatorList.aspx?House=%s&Year=%s&Number=%s'
    }

    def scrape(self, chamber, term):
        abbr = {'upper': 'S', 'lower': 'H'}
        years = []

        # Each term spans two years, so we need to scrape the 
        # members from both years and eliminate dupes
        for t in self.metadata['terms']:
            if term == t['name']:
                years.append(t['start_year'])
                years.append(t['end_year'])
                break

        members = {}
        for year in years: 
            if(year > 2005):
                chamber_indication = 'H' if chamber == 'lower' else 'S'
                url = self.urls['new'] % (chamber_indication, year, term)
                members = self.scrape_new_style(url, members)
            else:
                chamber_indication = 'rep' if chamber == 'lower' else 'sen'
                url = self.urls['old'] % (year, chamber_indication)
                members = self.scrape_old_style(url, members)

        for m in members:
            self.log(m)
            m = members[m]
            leg = Legislator(term, chamber, m['district'], m['name'], party=m['party'])
            leg.add_source(m['source'])
            self.save_legislator(leg)


    def scrape_new_style(self, url, members):
        """
        Scrapes legislator information from pages created since 2006
        """
        self.log(url)
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            for row in page.xpath('//table[contains(@id,"Members")]/tr')[1:]:
                tds = row.xpath('.//td')
                if(len(tds) < 4):
                    continue
                name = tds[0].text_content().strip()
                party = tds[1].text_content().strip()
                district = tds[2].text_content().strip()
                # Only keep if we don't already have member
                if(not members.has_key(name)):
                    self.log(name)
                    members[name] = { 'name': name, 'party': party, 'district': district, 'source': url }

            return members

    def scrape_old_style(self, url, members):
        """
        Scrapes legislator information from pages created prior to 2005
        """
        self.log(url)
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            for row in page.xpath('//table/tr')[1:]:
                tds = row.xpath('.//td')
                if(len(tds) < 4):
                    continue
                name = tds[0].text_content().strip()
                party = tds[1].text_content().strip()
                district = tds[2].text_content().strip()
                # Only keep if we don't already have member
                if(not members.has_key(name)):
                    self.log(name)
                    members[name] = { 'name': name, 'party': party, 'district': district, 'source': url }

            return members
