import datetime
import lxml.html
import re

from fiftystates.scrape.legislators import LegislatorScraper, Legislator

class WILegislatorScraper(LegislatorScraper):
    state = 'wi'

    def scrape(self, chamber, term):
        self.validate_term(term)

        if chamber == 'upper':
            url = "http://legis.wi.gov/w3asp/contact/legislatorslist.aspx?house=senate"
        else:
            url = "http://legis.wi.gov/w3asp/contact/legislatorslist.aspx?house=assembly"

        with self.urlopen(url) as body:
            page = lxml.html.fromstring(body)

            for row in page.cssselect("#ctl00_C_dgLegData tr"):
                if len(row.cssselect("td a")) > 0:
                    rep_url = list(row)[0].cssselect("a[href]")[0].get("href")

                    legpart = re.findall(r'([\w\-\,\s\.]+)\s+\(([\w])\)', list(row)[0].text_content())
                    if legpart:
                        full_name, party = legpart[0]

                        district = str(int(list(row)[2].text_content()))

                        leg = Legislator(term, chamber, district, full_name,
                                         party)
                        leg.add_source(rep_url)

                        leg = self.add_committees(leg, rep_url, term)
                        self.save_legislator(leg)

    def add_committees(self, legislator, rep_url, term):
        url = 'http://legis.wi.gov/w3asp/contact/' + rep_url + '&display=committee'
        body = unicode(self.urlopen(url), 'latin-1')
        cmts = lxml.html.fromstring(body).cssselect("#ctl00_C_lblCommInfo a")
        for c in map(lambda x: x.text_content().split('(')[0], list(cmts)):
            legislator.add_role('committee member', term, committee=c.strip())
        return legislator
