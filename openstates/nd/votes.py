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

fin_re = r"(?i).*(?P<bill_id>(S|H|J)(B|R|M) \d+).*(?P<passfail>(passed|lost)).*"
date_re = r".*(?P<date>(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY), .*\d{1,2},\s\d{4}).*"

class NDVoteScraper(VoteScraper):
    state = 'nd'

    def lxmlize(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page


    def scrape(self, chamber, session):
        if chamber not in PAGES:
            return

        url = PAGES[chamber]
        page = self.lxmlize(url)
        pdfs = page.xpath("//a[contains(@href, '.pdf')]")
        for pdf in pdfs:

            bill_id = None
            results = {}
            in_vote = False
            cur_date = None

            pdf_url = pdf.attrib['href']
            (path, response) = self.urlretrieve(pdf_url)
            data = convert_pdf(path, type='text')
            os.unlink(path)
            lines = data.splitlines()
            for line in lines:
                date = re.findall(date_re, line)
                if date != [] and not cur_date:
                    print date
                    date = date[0][0]
                    cur_date = datetime.datetime.strptime(date, "%A, %B %d, %Y")

                if line.strip() == "":
                    continue

                if line.strip() == 'ROLL CALL':
                    in_vote = True
                print cur_date, line
