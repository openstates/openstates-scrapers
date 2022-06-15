import datetime as dt
import lxml.html
import tempfile
import os
import re
from collections import defaultdict
from openstates.scrape import Scraper, Bill, VoteEvent
from openstates.utils import convert_pdf
from openstates.exceptions import EmptyScrape
from utils import LXMLMixin


class LABillScraper(Scraper, LXMLMixin):
    _chambers = {"S": "upper", "H": "lower", "J": "legislature"}

    _bill_types = {
        "B": "bill",
        "R": "resolution",
        "CR": "concurrent resolution",
        "SR": "study request",
        "CSR": "concurrent study request",
    }

    _session_ids = {
        "2017 1st Extraordinary Session": "171ES",
        "2017 2nd Extraordinary Session": "172ES",
        "2017": "17RS",
        "2018 1st Extraordinary Session": "181ES",
        "2018": "18RS",
        "2018 2nd Extraordinary Session": "182ES",
        "2018 3rd Extraordinary Session": "183ES",
        "2019": "19RS",
        "2020": "20RS",
        "2020s1": "201ES",
        "2020s2": "202ES",
        "2021": "21RS",
        "2022": "22RS",
        "2022s1": "221ES",
        "2022s2": "222ES",
    }

    def pdf_to_lxml(self, filename, type="html"):
        text = convert_pdf(filename, type)
        return lxml.html.fromstring(text)

    def _get_bill_abbreviations(self, session_id):
        page = self.lxmlize(
            "http://www.legis.la.gov/legis/BillSearch.aspx?" "sid={}".format(session_id)
        )

        if page.xpath("//span[contains(@id,'PageContent_labelNoBills')]"):
            raise EmptyScrape
            return

        select_options = page.xpath('//select[contains(@id, "InstTypes")]/option')

        bill_abbreviations = {"upper": [], "lower": []}

        for option in select_options:
            type_text = option.text
            if type_text.startswith("S"):
                bill_abbreviations["upper"].append(type_text)
            elif type_text.startswith("H"):
                bill_abbreviations["lower"].append(type_text)

        return bill_abbreviations

    def do_post_back(self, page, event_target, event_argument):
        form = page.xpath("//form[@id='aspnetForm']")[0]
        block = {
            name: value
            for name, value in [(obj.name, obj.value) for obj in form.xpath(".//input")]
        }
        block["__EVENTTARGET"] = event_target
        block["__EVENTARGUMENT"] = event_argument
        if form.method == "GET":
            ret = lxml.html.fromstring(self.get(form.action, data=block).text)
        elif form.method == "POST":
            ret = lxml.html.fromstring(self.post(form.action, data=block).text)
        else:
            raise AssertionError(
                "Unrecognized request type found: {}".format(form.method)
            )

        ret.make_links_absolute(form.action)
        return ret

    def bill_pages(self, url):
        response = self.get(url, allow_redirects=False)
        page = lxml.html.fromstring(response.text)
        page.make_links_absolute(url)
        yield page

        while True:
            hrefs = page.xpath("//a[text()=' > ']")
            if hrefs == [] or "disabled" in hrefs[0].attrib:
                return

            href = hrefs[0].attrib["href"]
            tokens = re.match(r".*\(\'(?P<token>.*)\',\'.*", href).groupdict()

            page = self.do_post_back(page, tokens["token"], "")
            if page is not None:
                yield page

    def scrape_bare_page(self, url):
        try:
            page = self.lxmlize(url)
            return page.xpath("//a")
        except lxml.etree.ParserError:
            return []

    def scrape(self, chamber=None, session=None):
        chambers = [chamber] if chamber else ["upper", "lower"]
        session_id = self._session_ids[session]
        # Scan bill abbreviation list if necessary.
        self._bill_abbreviations = self._get_bill_abbreviations(session_id)
        # there are duplicates we need to skip
        seen_bill_urls = set()
        for chamber in chambers:
            for bill_abbreviation in self._bill_abbreviations[chamber]:
                bill_list_url = "http://www.legis.la.gov/Legis/BillSearchListQ.aspx?s={}&r={}1*".format(
                    session_id, bill_abbreviation
                )
                bills_found = False
                for bill_page in self.bill_pages(bill_list_url):
                    for bill in bill_page.xpath(
                        "//a[contains(@href, 'BillInfo.aspx') and text()='more...']"
                    ):
                        bill_url = bill.attrib["href"]
                        if bill_url in seen_bill_urls:
                            continue
                        seen_bill_urls.add(bill_url)
                        bills_found = True
                        yield from self.scrape_bill_page(
                            chamber, session, bill_url, bill_abbreviation
                        )
                if not bills_found:
                    # If a session only has one legislative item of a given type
                    # (eg, some special sessions only have one `HB`), the bill list
                    # will redirect to its single bill's page
                    yield from self.scrape_bill_page(
                        chamber, session, bill_list_url, bill_abbreviation
                    )

    def get_one_xpath(self, page, xpath):
        ret = page.xpath(xpath)
        if len(ret) != 1:
            raise Exception
        return ret[0]

    def scrape_votes(self, bill, url):
        text = self.get(url).text
        page = lxml.html.fromstring(text)
        page.make_links_absolute(url)

        for a in page.xpath("//a[contains(@href, 'ViewDocument.aspx')]"):
            yield from self.scrape_vote(bill, a.text, a.attrib["href"])

    def scrape_vote(self, bill, name, url):
        match = re.match("^(Senate|House) Vote on [^,]*,(.*)$", name)

        if not match:
            return

        chamber = {"Senate": "upper", "House": "lower"}[match.group(1)]
        motion = match.group(2).strip()

        if motion.startswith("FINAL PASSAGE"):
            type = "passage"
        elif motion.startswith("AMENDMENT"):
            type = "amendment"
        elif "ON 3RD READING" in motion:
            type = "reading-3"
        else:
            type = []

        (fd, temp_path) = tempfile.mkstemp()
        self.urlretrieve(url, temp_path)

        html = self.pdf_to_lxml(temp_path)
        os.close(fd)
        os.remove(temp_path)

        vote_type = None
        body = html.xpath("string(/html/body)")

        date_match = re.search(r"Date: (\d{1,2}/\d{1,2}/\d{4})", body)
        try:
            date = date_match.group(1)
        except AttributeError:
            self.warning("BAD VOTE: date error")
            return

        start_date = dt.datetime.strptime(date, "%m/%d/%Y")
        d = defaultdict(list)
        for line in body.replace("\xa0", "\n").split("\n"):
            line = line.replace("&nbsp;", "").strip()
            # Skip blank lines and "Total --"
            if not line or "Total --" in line:
                continue

            if line in ("YEAS", "NAYS", "ABSENT"):
                vote_type = {"YEAS": "yes", "NAYS": "no", "ABSENT": "other"}[line]
            elif line in ("Total", "--"):
                vote_type = None
            elif vote_type:
                if vote_type == "yes":
                    d["yes"].append(line)
                elif vote_type == "no":
                    d["no"].append(line)
                elif vote_type == "other":
                    d["other"].append(line)

        yes_count = len(d["yes"])
        no_count = len(d["no"])
        other_count = len(d["other"])
        # The PDFs oddly don't say whether a vote passed or failed.
        # Hopefully passage just requires yes_votes > not_yes_votes
        if yes_count > (no_count + other_count):
            passed = True
        else:
            passed = False

        vote = VoteEvent(
            chamber=chamber,
            start_date=start_date.strftime("%Y-%m-%d"),
            motion_text=motion,
            result="pass" if passed else "fail",
            classification=type,
            bill=bill,
        )
        vote.set_count("yes", yes_count)
        vote.set_count("no", no_count)
        vote.set_count("other", other_count)
        for key, values in d.items():
            for item in values:
                vote.vote(key, item)
        vote.add_source(url)
        yield vote

    def scrape_bill_page(self, chamber, session, bill_url, bill_abbreviation):
        page = self.lxmlize(bill_url)
        author = self.get_one_xpath(page, "//a[@id='ctl00_PageBody_LinkAuthor']/text()")

        def sbp(x):
            return self.scrape_bare_page(
                page.xpath("//a[contains(text(), '%s')]" % (x))[0].attrib["href"]
            )

        authors = [x.text for x in sbp("Authors")]

        try:
            digests = sbp("Digests")
        except IndexError:
            digests = []

        try:
            versions = sbp("Text")
        except IndexError:
            versions = []

        try:
            amendments = sbp("Amendments")
        except IndexError:
            amendments = []

        title = page.xpath("//span[@id='ctl00_PageBody_LabelShortTitle']/text()")[0]
        title = title.replace("\u00a0\u00a0", " ")
        actions = page.xpath(
            "//div[@id='ctl00_PageBody_PanelBillInfo']/"
            "/table[@style='font-size:small']/tr"
        )

        bill_id = page.xpath("//span[@id='ctl00_PageBody_LabelBillID']/text()")[0]

        bill_type = self._bill_types[bill_abbreviation[1:]]
        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=title,
            classification=bill_type,
        )
        bill.add_source(bill_url)

        authors.remove(author)
        bill.add_sponsorship(
            author, classification="primary", entity_type="person", primary=True
        )
        for author in authors:
            bill.add_sponsorship(
                author, classification="cosponsor", entity_type="person", primary=False
            )

        for digest in digests:
            bill.add_document_link(
                note=digest.text,
                url=digest.attrib["href"],
                media_type="application/pdf",
            )

        for version in versions:
            bill.add_version_link(
                note=version.text,
                url=version.attrib["href"],
                media_type="application/pdf",
            )

        for amendment in amendments:
            if "href" in amendment.attrib:
                bill.add_version_link(
                    note=amendment.text,
                    url=amendment.attrib["href"],
                    media_type="application/pdf",
                )

        flags = {
            "prefiled": ["filing"],
            "referred to the committee": ["referral-committee"],
            "sent to the house": ["passage"],
            "ordered returned to the house": ["passage"],
            "ordered to the senate": ["passage"],
            "signed by the governor": ["executive-signature"],
            "sent to the governor": ["executive-receipt"],
            "becomes Act": ["became-law"],
            "vetoed by the governor": ["executive-veto"],
        }

        try:
            votes_link = page.xpath("//a[text() = 'Votes']")[0]
            yield from self.scrape_votes(bill, votes_link.attrib["href"])
        except IndexError:
            # Some bills don't have any votes
            pass

        for action in actions:
            date, chamber, page, text = [x.text for x in action.xpath(".//td")]
            session_year = self.jurisdiction.legislative_sessions[-1]["start_date"][0:4]
            # Session is April -> June. Prefiles look like they're in
            # January at earliest.
            date += "/{}".format(session_year)
            date = dt.datetime.strptime(date, "%m/%d/%Y")
            chamber = self._chambers[chamber]

            cat = []
            for flag in flags:
                if flag in text.lower():
                    cat += flags[flag]

            bill.add_action(
                description=text,
                date=date.strftime("%Y-%m-%d"),
                chamber=chamber,
                classification=cat,
            )

        yield bill
