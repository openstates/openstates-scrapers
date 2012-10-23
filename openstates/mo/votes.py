from billy.scrape.votes import VoteScraper, Vote
from billy.scrape.utils import convert_pdf

import lxml


SENATE_URL = 'http://www.senate.mo.gov/12info/jrnlist/journals.aspx'
HOUSE_URL = 'http://www.house.mo.gov/journallist.aspx'


class MOVoteScraper(VoteScraper):
    state = 'mo'

    def lxmlize(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def get_pdf(self, url):
        (path, response) = self.urlretrieve(url)
        data = convert_pdf(path, type='text')
        return data

    def scrape_senate(self):
        url = SENATE_URL
        page = self.lxmlize(url)
        journs = page.xpath("//table")[0].xpath(".//a")
        for a in journs:
            data = self.get_pdf(a.attrib['href'])
            print data

    def scrape_house(self):
        url = HOUSE_URL
        page = self.lxmlize(url)
        journs = page.xpath(
            "//span[@id='ContentPlaceHolder1_lblJournalListing']//a")
        for a in journs:
            data = self.get_pdf(a.attrib['href'])
            print data

    def scrape(self, chamber, session):
        if chamber == 'upper':
            self.scrape_senate()
        elif chamber == 'lower':
            self.scrape_house()
