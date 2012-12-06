from billy.scrape.legislators import Legislator, LegislatorScraper
from billy.scrape import NoDataForPeriod
import lxml.html
import logging
import re

logger = logging.getLogger('openstates')

class NDLegislatorScraper(LegislatorScraper):
    jurisdiction = 'nd'

    def scrape(self, term, chambers):
        self.validate_term(term, latest_only=True)

        # figuring out starting year from metadata
        for t in self.metadata['terms']:
            if t['name'] == term:
                start_year = t['start_year']
                break

        root = "http://www.legis.nd.gov/assembly"
        main_url = "%s/%s-%s/members/members-by-district" % (
            root,
            term,
            start_year
        )

        with self.urlopen(main_url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(main_url)
            for district in page.xpath("//h2//a[contains(text(), 'District')]"):
                dis = district.text.replace("District ", "")
                for person in district.getparent().getnext().xpath(".//a"):
                    self.scrape_legislator_page(
                        term,
                        dis,
                        person.attrib['href']
                    )


    def scrape_legislator_page(self, term, district, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)
            name = page.xpath("//h1[@id='page-title']/text()")[0]
