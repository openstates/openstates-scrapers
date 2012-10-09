from billy.scrape.votes import VoteScraper, Vote
import subprocess
import lxml
import os

journals = "http://www.leg.state.co.us/CLICS/CLICS%s/csljournals.nsf/jouNav?Openform&%s"

# session - 2012A
# chamber - last argument, House / Senate


class COVoteScraper(VoteScraper):
    state = 'co'

    def lxmlize(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def scrape_senate(self, session):
        url = journals % (session, 'Senate')
        page = self.lxmlize(url)
        hrefs = page.xpath("//font//a")
        for href in hrefs:
            (path, response) = self.urlretrieve(href.attrib['href'])
            subprocess.check_call([
                "pdftotext", "-layout", path
            ])
            txt = "%s.txt" % (path)



            os.unlink(path)
            os.unlink(txt)

    def scrape_house(self, session):
        pass

    def scrape(self, chamber, session):
        if chamber == 'upper':
            self.scrape_senate(session)
        if chamber == 'lower':
            self.scrape_house(session)
