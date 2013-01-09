from collections import defaultdict
from urlparse import urljoin
from datetime import datetime
import lxml.html
from billy.scrape import NoDataForPeriod, ScrapeError
from billy.scrape.bills import Bill, BillScraper
from billy.scrape.votes import Vote
from .actions import NDCategorizer
import re

base_url = "http://www.legis.nd.gov/assembly/%s-%s/subject-index/major-topic.html"


class NDBillScraper(BillScraper):
    """
    Scrapes available legislative information from the website of the North
    Dakota legislature and stores it in the openstates  backend.
    """
    jurisdiction = 'nd'
    categorizer = NDCategorizer()

    def scrape_actions(self, session, subject, href, bid):
        with self.urlopen(href) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(href)
        ttable, table = page.xpath(
            "//table[@summary='Measure Number Breakdown']"
        )

        ttrows = ttable.xpath(".//tr")
        descr = ttrows[-1]
        title = re.sub("\s+", " ", descr.text_content()).strip()
        ttrows = ttrows[:-1]
        chamber = {
            "H": "lower",
            "S": "upper"
        }[bid[0]]

        bill = Bill(session,
                    chamber,
                    bid,
                    title,
                    subject=subject)

        bill.add_source(href)

        for row in ttrows:
            sponsors = row.text_content().strip()
            sinf = re.match(
                "(?i)introduced by( (rep\.|sen\.))? (?P<sponsors>.*)",
                sponsors
            )
            if sinf:
                sponsors = sinf.groupdict()
                for sponsor in [
                    x.strip() for x in sponsors['sponsors'].split(",")
                ]:
                    bill.add_sponsor('primary',
                                     sponsor)


        dt = None
        for row in table.xpath(".//tr"):
            if row.text_content().strip() == '':
                continue

            row = row.xpath("./*")
            row = [x.text_content().strip() for x in row]

            if len(row) > 3:
                row = row[:3]

            date, chamber, action = row

            try:
                chamber = {
                    "House": "lower",
                    "Senate": "upper"
                }[chamber]
            except KeyError:
                chamber = "other"

            if date != '':
                dt = datetime.strptime(date, "%m/%d")

            kwargs = self.categorizer.categorize(action)

            bill.add_action(chamber,
                            action,
                            dt,
                            **kwargs)


        version_url = page.xpath("//a[contains(text(), 'Versions')]")
        if len(version_url) == 1:
            href = version_url[0].attrib['href']
            bill = self.scrape_versions(bill, href)

        self.save_bill(bill)

    def scrape_versions(self, bill, href):
        with self.urlopen(href) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(href)
        versions = page.xpath("//a[contains(@href, '/documents/')]")
        for version in versions:
            name, href = version.text, version.attrib['href']
            bill.add_version(name, href, mimetype='application/pdf')

        return bill

    def scrape_subject(self, session, href, subject):
        with self.urlopen(href) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(href)
        bills = page.xpath("//a[contains(@href, 'bill-actions')]")
        for bill in bills:
            bt = bill.text_content()
            typ, idd, _, = bt.split()
            bid = "%s %s" % (typ, idd)
            self.scrape_actions(session, subject, bill.attrib['href'], bid)

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
            self.scrape_subject(term, href, subject.text)
