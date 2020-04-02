import lxml.html
from openstates_core.scrape import Scraper, Organization


class MACommitteeScraper(Scraper):
    def scrape(self, chamber=None):
        page_types = []

        if chamber == "upper" or chamber is None:
            page_types += ["Senate", "Joint"]
        if chamber == "lower" or chamber is None:
            page_types += ["House"]

        chamber_mapping = {"Senate": "upper", "House": "lower", "Joint": "legislature"}

        for page_type in page_types:
            url = "https://www.malegislature.gov/Committees/" + page_type

            html = self.get(url).text
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute("http://www.malegislature.gov")

            for com_url in doc.xpath('//ul[@class="committeeList"]/li/a/@href'):
                chamber = chamber_mapping[page_type]
                yield self.scrape_committee(chamber, com_url)

    def scrape_committee(self, chamber, url):
        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        name = doc.xpath("//title/text()")[0]
        com = Organization(name, chamber=chamber, classification="committee")
        com.add_source(url)

        members = doc.xpath('//a[contains(@href, "/Legislators/Profile")]')
        for member in members:
            title = member.xpath("../span")
            role = title[0].text.lower() if title else "member"
            com.add_member(member.text, role)

        if members:
            return com
