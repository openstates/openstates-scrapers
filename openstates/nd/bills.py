from datetime import datetime
import lxml.html
from pupa.scrape import Scraper, Bill
from .actions import NDCategorizer
import re
from openstates.utils import LXMLMixin


class NDBillScraper(Scraper, LXMLMixin):
    """
    Scrapes available legislative information from the website of the North
    Dakota legislature and stores it in the openstates  backend.
    """

    categorizer = NDCategorizer()

    house_list_url = "http://www.legis.nd.gov/assembly/%s-%s/bill-text/house-bill.html"
    senate_list_url = (
        "http://www.legis.nd.gov/assembly/%s-%s/bill-text/senate-bill.html"
    )
    subjects_url = (
        "http://www.legis.nd.gov/assembly/%s-%s/subject-index/major-topic.html"
    )

    def scrape_actions(self, session, href):
        page = self.lxmlize(href)

        (bid,) = page.xpath('//h1[@id="page-title"]/text()')
        bid = re.sub(r"^Bill Actions for ", "", bid)
        subjects = self.subjects.get(bid, [])

        # some pages say "Measure Number Breakdown", others "Bill..."
        table = page.xpath("//table[contains(@summary, 'Number Breakdown')]")
        table = table[0]
        ttrows = page.xpath("//div[@id='application']/p")
        descr = ttrows[-2]

        title = re.sub(r"\s+", " ", descr.text_content()).strip()
        ttrows = ttrows[:-1]

        chamber = {"H": "lower", "S": "upper"}[bid[0]]

        type_ = bid[1:3]
        bill_type = "bill"
        if type_.startswith("B"):
            bill_type = "bill"

        if type_.startswith("R"):
            bill_type = "resolution"

        if type_ == "CR":
            bill_type = "concurrent resolution"

        bill = Bill(
            bid,
            legislative_session=session,
            chamber=chamber,
            title=title,
            classification=bill_type,
        )
        bill.subject = subjects
        bill.add_source(href)

        for row in ttrows:
            if isinstance(row, lxml.html.HtmlComment):
                continue  # ignore HTML comments, no text_content()
            sponsors = row.text_content().strip()
            sinf = re.match(
                r"(?i)introduced by( (rep\.|sen\.))? (?P<sponsors>.*)", sponsors
            )
            if sinf:
                sponsors = sinf.groupdict()
                for sponsor in [x.strip() for x in sponsors["sponsors"].split(",")]:
                    bill.add_sponsorship(
                        sponsor,
                        classification="primary",
                        entity_type="person",
                        primary=True,
                    )

        dt = None
        oldchamber = "other"
        for row in table.xpath(".//tr"):
            if row.text_content().strip() == "":
                continue

            if "Meeting Description" in [x.strip() for x in row.xpath(".//th/text()")]:
                continue

            row = row.xpath("./*")
            row = [x.text_content().strip() for x in row]

            if len(row) > 3:
                row = row[:3]

            date, chamber, action = row

            try:
                chamber = {"House": "lower", "Senate": "upper"}[chamber]
                oldchamber = chamber
            except KeyError:
                chamber = oldchamber

            if date != "":
                dt = datetime.strptime("%s %s" % (date, self.year), "%m/%d %Y")

            classif = self.categorizer.categorize(action)

            bill.add_action(
                chamber=chamber,
                description=action,
                date=dt.strftime("%Y-%m-%d"),
                classification=classif["classification"],
            )

        version_url = page.xpath("//a[contains(text(), 'Versions')]")
        if len(version_url) == 1:
            href = version_url[0].attrib["href"]
            bill = self.scrape_versions(bill, href)

        yield bill

    def scrape_versions(self, bill, href):
        page = self.lxmlize(href)
        version_rows = page.xpath('//table[contains(@summary, "Breakdown")]//tr')

        for row in version_rows[1:]:
            try:
                (name,) = row.xpath("td[2]/text()")
            except ValueError:
                self.warning("No action name found to use as bill version name")
                (name,) = row.xpath("td[1]/a/text()")
            (url,) = row.xpath("td[1]/a/@href")
            bill.add_version_link(note=name, url=url, media_type="application/pdf")

            try:
                (marked_up_url,) = row.xpath("td[3]/a/@href")
                bill.add_version_link(
                    "{} (Marked Up)".format(name),
                    marked_up_url,
                    media_type="application/pdf",
                )
            except ValueError:
                pass

        return bill

    def scrape_subjects(self, session):
        page = self.get(self.subjects_url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(self.subjects_url)
        subjects = page.xpath(
            "//div[@id='application']//a[not(contains(@href, 'major-topic'))]"
        )
        for subject in subjects:
            subject_name = subject.xpath("text()")
            if (
                subject_name == []
                or subject_name[0].strip() == ""
                or "href" not in subject.attrib
            ):
                continue

            href = subject.attrib["href"]
            self.scrape_subject(href, subject.text.strip())

    def scrape_subject(self, href, subject):
        page = self.get(href).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(href)
        bills = page.xpath("//a[contains(@href, 'bill-actions')]")
        for bill in bills:
            bt = bill.text_content().strip().split()
            try:
                typ, idd = bt[0], bt[1]
                bid = "%s %s" % (typ, idd)
                if bid not in self.subjects.keys():
                    self.subjects[bid] = []
                self.subjects[bid].append(subject)
            except IndexError:
                self.warning("Bill ID and Type Not Found!")

    def scrape(self, session=None, chamber=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)
        # chambers = [chamber] if chamber else ['upper', 'lower']
        # figuring out starting year from metadata
        for item in self.jurisdiction.legislative_sessions:
            if item["identifier"] == session:
                start_year = item["start_date"][:4]
                self.year = start_year
                break
        # Get the subjects for every bill
        # Sometimes, at least with prefiles, a bill will not be given subjects
        self.subjects_url = self.subjects_url % (session, start_year)
        self.subjects = {}
        self.scrape_subjects(session)

        for chamber, url in {
            "lower": self.house_list_url % (session, start_year),
            "upper": self.senate_list_url % (session, start_year),
        }.items():
            doc = self.lxmlize(url)
            bill_urls = doc.xpath(
                "//table["
                'contains(@summary, "Bills")'
                'or contains(@summary, "Resolutions")'
                "]//tr/th/a/@href"
            )
            # Each version of a bill is its own row, so de-dup the links
            for bill_url in set(bill_urls):
                yield from self.scrape_actions(session, bill_url)
