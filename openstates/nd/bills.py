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
        page = self.urlopen(href)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(href)
        table = page.xpath(
            "//table[@summary='Bill Number Breakdown']"
        )

        if len(table) > 1:  # Pre-2013 pages.
            ttable, table = table
            ttrows = ttable.xpath(".//tr")
            descr = ttrows[-1]
        else:
            table = table[0]
            curnode = page.xpath("//div[@id='fastpath']")[0].getnext()
            ret = []
            while curnode.tag != "table":
                curnode = curnode.getnext()
                ret.append(curnode)
            ttrows = ret
            descr = page.xpath("//div[@class='section']//p")[-2]

        title = re.sub("\s+", " ", descr.text_content()).strip()
        ttrows = ttrows[:-1]

        chamber = {
            "H": "lower",
            "S": "upper"
        }[bid[0]]

        type_ = bid[1:3]
        bill_type = "bill"
        if type_.startswith("B"):
            bill_type = "bill"

        if type_.startswith("R"):
            bill_type = "resolution"

        if type_ == "CR":
            bill_type = "concurrent resolution"

        bill = Bill(session,
                    chamber,
                    bid,
                    title,
                    subject=subject,
                    type=bill_type)

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
        oldchamber = 'other'
        for row in table.xpath(".//tr"):
            if row.text_content().strip() == '':
                continue

            if "Meeting Description" in [
                x.strip() for x in row.xpath(".//th/text()")
            ]:
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
                oldchamber = chamber
            except KeyError:
                chamber = oldchamber

            if date != '':
                dt = datetime.strptime("%s %s" % (date, self.year), "%m/%d %Y")

            kwargs = self.categorizer.categorize(action)

            bill.add_action(chamber, action, dt, **kwargs)

        version_url = page.xpath("//a[contains(text(), 'Versions')]")
        if len(version_url) == 1:
            href = version_url[0].attrib['href']
            bill = self.scrape_versions(bill, href)

        self.save_bill(bill)

    def scrape_versions(self, bill, href):
        page = self.urlopen(href)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(href)
        versions = page.xpath("//a[contains(@href, '/documents/')]")
        for version in versions:
            name, href = version.text, version.attrib['href']
            bill.add_version(name, href, mimetype='application/pdf')

        return bill

    def scrape_subject(self, session, href, subject):
        page = self.urlopen(href)
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
                self.year = start_year
                break

        url = base_url % (term, start_year)
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        subjects = page.xpath(
            "//div[@id='application']"
            "//a[not(contains(@href, 'major-topic'))]"
        )
        for subject in subjects:
            subject_name = subject.xpath("text()")
            if subject_name == [] \
               or subject_name[0].strip() == '' \
               or 'href' not in subject.attrib:
                continue

            href = subject.attrib['href']
            self.scrape_subject(term, href, subject.text.strip())
