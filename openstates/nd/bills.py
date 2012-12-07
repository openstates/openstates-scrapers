from collections import defaultdict
from urlparse import urljoin
from datetime import datetime
import lxml.html
from billy.scrape import NoDataForPeriod, ScrapeError
from billy.scrape.bills import Bill, BillScraper
from billy.scrape.votes import Vote

base_url = "http://www.legis.nd.gov/assembly/%s-%s/subject-index/major-topic.html"


class NDBillScraper(BillScraper):
    """
    Scrapes available legislative information from the website of the North
    Dakota legislature and stores it in the openstates  backend.
    """
    jurisdiction = 'nd'

    def scrape_subject(self, href):
        with self.urlopen(href) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(href)
        bills = page.xpath("//a[contains(@href, 'bill-actions')]")
        print bills

    def scrape(self, term, chambers):
        # figuring out starting year from metadata
        for t in self.metadata['terms']:
            if t['name'] == term:
                start_year = t['start_year']
                break

        url = base_url % (term, start_year)
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        subjects = page.xpath(
            "//table[@summary='Links table']//"
            "a[not(contains(@href, 'major-topic'))]"
        )
        for subject in subjects:
            subject_name = subject.xpath("text()")
            if subject_name == [] \
               or subject_name[0].strip() == '' \
               or 'href' not in subject.attrib:
                continue

            href = subject.attrib['href']
            self.scrape_subject(href)
