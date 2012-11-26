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

    def scrape_upper(self, href, chamber, term):
        page = self.lxmlize(href)
        title, name = [
            x.text_content() for x in page.xpath("//div[@class='senateh3']")
        ]
        print name

    def scrape_lower(self, href, chamber, term):
        pass

    def scrape(self, chamber, term):
        page = self.lxmlize(URLS[chamber])
        t = page.xpath("//div[@class='ggaMasterContent']/table[@width='100%']")
        if len(t) != 1:
            raise Exception("Something's broke with the scraper. Root "
                            "legislator list isn't what I think it was.")
        t = t[0]
        legislators = t.xpath(".//a[contains(@href, 'member.aspx')]")
        for legislator in legislators:
            href = legislator.attrib['href']
            getattr(self, "scrape_%s" % (chamber))(href, chamber, term)
