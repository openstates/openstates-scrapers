import lxml
from openstates.scrape import Scraper  # , Organization


class VICommitteeScraper(Scraper):
    def scrape(self, session, chambers):

        com_url = (
            "http://www.legvi.org/index.php/"
            "committees/committees-of-the-31st-legislature"
        )
        doc = lxml.html.fromstring(self.get(url=com_url).text)

        coms = doc.xpath(
            '//*[@id="sp-component"]/article/section/table/'
            "tbody/tr/td[1]/p/span/strong/span/text()"
        )
        index = 0
        for com in coms:
            print(com)
            members = doc.xpath(
                '//p/following::p[contains(.,"{} consists of")]'.format(com)
            )
            print(members)
            index = index + 1
