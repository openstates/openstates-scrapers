from billy.scrape.votes import VoteScraper, Vote
from billy.scrape.utils import convert_pdf
import datetime
import subprocess
import lxml
import os
import re


PAGES = {
    "upper":
      "http://www.legis.nd.gov/assembly/62-2011/journals/senate-journal.html",
    "lower":
      "http://www.legis.nd.gov/assembly/62-2011/journals/house-journal.html"
}


class NDVoteScraper(VoteScraper):
    state = 'nd'

    def lxmlize(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page


    def scrape(self, chamber, session):
        return

        if chamber not in PAGES:
            return

        url = PAGES[chamber]
        page = self.lxmlize(url)
        pdfs = page.xpath("//a[contains(@href, '.pdf')]")
        for pdf in pdfs:
            print pdf.attrib['href']
