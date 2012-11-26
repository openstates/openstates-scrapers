from billy.scrape.legislators import LegislatorScraper, Legislator
import lxml

URLS = {
    "upper": "http://www.senate.ga.gov/senators/en-US/SenateMembersList.aspx",
    "lower": "http://www.house.ga.gov/Representatives/en-US/HouseMembersList.aspx"
}

class GALegislatorScraper(LegislatorScraper):
    state = 'ga'

    def lxmlize(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def scrape(self, chamber, term):
        page = self.lxmlize(URLS[chamber])
        print page
