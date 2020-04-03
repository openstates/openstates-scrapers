import re
import datetime
import urllib.parse
import scrapelib
from collections import defaultdict
import lxml.html

from openstates_core.scrape import Scraper, Bill

from scrapers.utils import LXMLMixin

# Base URL for the details of a given bill.
BILL_DETAIL_URL_BASE = "https://www.revisor.mn.gov/bills/"
BILL_DETAIL_URL = "https://www.revisor.mn.gov/bills/bill.php" "?b=%s&f=%s&ssn=0&y=%s"

# The versions of a bill use a different base URL.
VERSION_URL_BASE = "https://www.revisor.mn.gov/bills/"
VERSION_URL = (
    "https://www.revisor.mn.gov/bin/getbill.php"
    "?session_year=%s&session_number=%s&number=%s&version=list"
)

# Search URL
BILL_SEARCH_URL = (
    "https://www.revisor.mn.gov/bills/"
    "status_result.php?body=%s&session=%s&bill=%s-%s"
    "&bill_type=%s&submit_bill=GO"
)

# https://www.revisor.mn.gov/bills/status_search.php?body=House
# select[name="session"] values
SITE_IDS = {
    "2009-2010": "0862009",
    "2010 1st Special Session": "1862010",
    "2010 2nd Special Session": "2862010",
    "2011-2012": "0872011",
    "2011s1": "1872011",
    "2012s1": "1872012",
    "2013-2014": "0882013",
    "2013s1": "1882013",
    "2015-2016": "0892015",
    "2015s1": "1892015",
    "2017-2018": "0902017",
    "2017s1": "1902017",
    "2019-2020": "0912019",
    "2019s1": "1912019",
}


class MNBillScraper(Scraper, LXMLMixin):
    # For testing purposes, this will do a lite version of things.  If
    # testing_bills is set, only these bills will be scraped.  Use SF0077
    testing = False
    testing_bills = ["SF1952"]

    # Regular expressions to match category of actions
    _categorizers = (
        ("Introduced", "introduction"),
        (
            "Introduction and first reading, referred to",
            ["introduction", "referral-committee"],
        ),
        (
            "Committee report, to pass as amended and re-refer to",
            ["referral-committee"],
        ),
        ("Introduction and first reading", "introduction"),
        ("Referred (by Chair )?to", "referral-committee"),
        ("Second reading", "reading-2"),
        (
            "Comm(ittee)? report: (T|t)o pass( as amended)? and re-refer(red)? to",
            ["committee-passage", "referral-committee"],
        ),
        ("Comm(ittee)? report: (T|t)o pass( as amended)?", "committee-passage"),
        ("Comm(ittee)? report, to adopt", "committee-passage"),
        ("Third reading Passed", "passage"),
        ("Bill was passed", "passage"),
        ("Third reading", "reading-3"),
        ("Governor('s action)? (A|a)pproval", "executive-signature"),
        (".+? (V|v)eto", "executive-veto"),
        ("Presented to Governor", "executive-receipt"),
        ("Amended", "amendment-passage"),
        ("Amendments offered", "amendment-introduction"),
        (" repassed ", "passage"),
        ("Resolution was adopted", "passage"),
        ("(?i)^Adopted", "passage"),
        (" re-referred ", "referral-committee"),
        ("Received from", "introduction"),
    )

    def scrape(self, session=None, chamber=None):
        """
        Scrape all bills for a given chamber and a given session.

        This method uses the legislature's search page to collect all the bills
        for a given chamber and session.
        """
        # If testing, print a message
        if self.is_testing():
            self.debug("TESTING...")

        # SSL broken as of Jan 2020
        self.verify = False

        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        chambers = [chamber] if chamber else ["upper", "lower"]
        for chamber in chambers:

            # Get bill topics for matching later
            self.get_bill_topics(chamber, session)

            # If testing and certain bills to test, only test those
            if self.is_testing() and len(self.testing_bills) > 0:
                for b in self.testing_bills:
                    bill_url = BILL_DETAIL_URL % (self.search_chamber(chamber), b, 2017)
                    version_url = VERSION_URL % (
                        self.search_session(session)[-4:],
                        self.search_session(session)[0],
                        b,
                    )
                    yield self.get_bill_info(chamber, session, bill_url, version_url)

            else:

                # Find list of all bills
                bills = self.get_full_bill_list(chamber, session)

                # Get each bill
                for b in bills:
                    yield self.get_bill_info(
                        chamber, session, b["bill_url"], b["version_url"]
                    )

    def get_full_bill_list(self, chamber, session):
        """
        Uses the legislator search to get a full list of bills.  Search page
        returns a maximum of 500 results.
        """
        search_chamber = self.search_chamber(chamber)
        search_session = self.search_session(session)
        total_rows = list()
        bills = []
        stride = 500
        start = 0

        # If testing, only do a few
        total = 300 if self.is_testing() else 10000

        # Get total list of rows
        for bill_type in ("bill", "concurrent", "resolution"):
            for start in range(0, total, stride):
                # body: "House" or "Senate"
                # session: legislative session id
                # bill: Range start-end (e.g. 1-10)
                url = BILL_SEARCH_URL % (
                    search_chamber,
                    search_session,
                    start,
                    start + stride,
                    bill_type,
                )
                # Parse HTML
                html = self.get(url).text
                doc = lxml.html.fromstring(html)

                # get table containing bills
                rows = doc.xpath('//table[contains(@class,"table")]/tbody/tr')
                total_rows.extend(rows)
                # Out of rows
                if len(rows) == 0:
                    self.debug("Total Bills Found: %d" % len(total_rows))
                    break

        # Go through each row found
        for row in total_rows:
            bill = {}

            # Second column: status link
            bill_details_link = row.xpath("td[2]/a")[0]
            bill["bill_url"] = urllib.parse.urljoin(
                BILL_DETAIL_URL_BASE, bill_details_link.get("href")
            )

            # Version link sometimes goes to wrong place, forge it
            bill["version_url"] = VERSION_URL % (
                search_session[-4:],
                search_session[0],
                bill_details_link.text_content(),
            )

            bills.append(bill)

        return bills

    def get_bill_info(self, chamber, session, bill_detail_url, version_list_url):
        """
        Extracts all the requested info for a given bill.

        Calls the parent's methods to enter the results into JSON files.
        """
        chamber = "lower" if chamber.lower() == "house" else chamber
        chamber = "upper" if chamber.lower() == "senate" else chamber

        # Get html and parse
        doc = self.lxmlize(bill_detail_url)

        # Check if bill hasn't been transmitted to the other chamber yet
        transmit_check = self.get_node(
            doc, '//h1[text()[contains(.,"Bills")]]/following-sibling::ul/li/text()'
        )
        if (
            transmit_check is not None
            and "has not been transmitted" in transmit_check.strip()
        ):
            self.logger.debug(
                "Bill has not been transmitted to other chamber "
                "... skipping {0}".format(bill_detail_url)
            )
            return

        # Get the basic parts of the bill
        bill_id = self.get_node(
            doc, '//h1[contains(@class,"card-title float-left mr-4")]/text()'
        )
        self.logger.debug(bill_id)
        bill_title_text = self.get_node(
            doc, '//h2[text()[contains(.,"Description")]]/following-sibling::p/text()'
        )
        if bill_title_text is not None:
            bill_title = bill_title_text.strip()
        else:
            long_desc_url = self.get_node(
                doc, '//a[text()[contains(.,"Long Description")]]/@href'
            )
            long_desc_page = self.lxmlize(long_desc_url)
            long_desc_text = self.get_node(
                long_desc_page, "//h1/" "following-sibling::p/text()"
            )
            if long_desc_text is not None:
                bill_title = long_desc_text.strip()
            else:
                bill_title = "No title found."
                self.logger.warning("No title found for {}.".format(bill_id))
        self.logger.debug(bill_title)
        bill_type = {"F": "bill", "R": "resolution", "C": "concurrent resolution"}[
            bill_id[1].upper()
        ]
        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=bill_title,
            classification=bill_type,
        )

        # Add source
        bill.add_source(bill_detail_url)

        for subject in self._subject_mapping[bill_id]:
            bill.add_subject(subject)

        # Get companion bill.
        companion = doc.xpath(
            '//table[@class="status_info"]//tr[1]/td[2]'
            '/a[starts-with(@href, "?")]/text()'
        )
        companion = self.make_bill_id(companion[0]) if len(companion) > 0 else None
        companion_chamber = self.chamber_from_bill(companion)
        if companion is not None:
            bill.add_companion(companion, chamber=companion_chamber)

        # Grab sponsors
        bill = self.extract_sponsors(bill, doc, chamber)

        # Add Actions performed on the bill.
        bill = self.extract_actions(bill, doc, chamber)

        # Get all versions of the bill.
        bill = self.extract_versions(bill, doc, chamber, version_list_url)

        yield bill

    def get_bill_topics(self, chamber, session):
        """
        Uses the leg search to map topics to bills.
        """
        search_chamber = {"lower": "House", "upper": "Senate"}[chamber]
        search_session = self.search_session(session)
        self._subject_mapping = defaultdict(list)

        url = "%sstatus_search.php?body=%s&search=topic&session=%s" % (
            BILL_DETAIL_URL_BASE,
            search_chamber,
            search_session,
        )
        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        # For testing purposes, we don't really care about getting
        # all the topics, just a few
        if self.is_testing():
            option_set = doc.xpath('//select[@name="topic[]"]/option')[0:5]
        else:
            option_set = doc.xpath('//select[@name="topic[]"]/option')[0:]

        for option in option_set:
            # Subjects look like "Name of Subject (##)" -- split off the #
            subject = option.text.rsplit(" (")[0]
            value = option.get("value")
            opt_url = (
                "%sstatus_result.php?body=%s&search=topic&session=%s"
                "&topic[]=%s&submit_topic=GO"
                % (BILL_DETAIL_URL_BASE, search_chamber, search_session, value)
            )
            opt_html = self.get(opt_url).text
            opt_doc = lxml.html.fromstring(opt_html)
            for bill in opt_doc.xpath("//table/tbody/tr/td[2]/a/text()"):
                bill = self.make_bill_id(bill)
                self._subject_mapping[bill].append(subject)

    def extract_actions(self, bill, doc, current_chamber):
        """
        Extract the actions taken on a bill.
        A bill can have actions taken from either chamber.  The current
        chamber's actions will be the first table of actions. The other
        chamber's actions will be in the second table.
        """

        bill_actions = list()
        action_tables = doc.xpath('//table[contains(@class,"actions")]')

        for cur_table in action_tables:
            for row in cur_table.xpath(".//tr"):
                bill_action = dict()

                # Split up columns
                date_col, the_rest = row.xpath("td")

                # The second column can hold a link to full text
                # and pages (what should be in another column),
                # but also links to committee elements or other spanned
                # content.
                action_date = date_col.text_content().strip()
                action_text = row.xpath("td[2]/div/div")[0].text_content().strip()

                committee = the_rest.xpath("a[contains(@href,'committee')]/text()")
                extra = "".join(the_rest.xpath("span[not(@style)]/text() | a/text()"))
                # skip non-actions (don't have date)
                if action_text in (
                    "Chapter number",
                    "See also",
                    "See",
                    "Effective date",
                    "Secretary of State",
                ):
                    continue

                # dates are really inconsistent here, sometimes in action_text
                try:
                    action_date = datetime.datetime.strptime(
                        action_date, "%m/%d/%Y"
                    ).date()
                except ValueError:
                    try:
                        action_date = datetime.datetime.strptime(
                            extra, "%m/%d/%y"
                        ).date()
                    except ValueError:
                        try:
                            action_date = datetime.datetime.strptime(
                                extra, "%m/%d/%Y"
                            ).date()
                        except ValueError:
                            self.warning("ACTION without date: %s" % action_text)
                            continue

                # categorize actions
                action_type = None
                for pattern, atype in self._categorizers:
                    if re.match(pattern, action_text):
                        action_type = atype
                        if "referral-committee" in action_type and len(committee) > 0:
                            bill_action["committees"] = committee[0]
                        break

                if extra:
                    action_text += " " + extra
                bill_action["action_text"] = action_text
                if isinstance(action_type, list):
                    for atype in action_type:
                        if atype is not None and (
                            atype.startswith("governor")
                            or atype.startswith("executive")
                            or atype.startswith("became")
                        ):
                            bill_action["action_chamber"] = "executive"
                            break
                    else:
                        bill_action["action_chamber"] = current_chamber
                else:
                    if action_type is not None and (
                        action_type.startswith("governor")
                        or action_type.startswith("executive")
                        or action_type.startswith("became")
                    ):
                        bill_action["action_chamber"] = "executive"
                    else:
                        bill_action["action_chamber"] = current_chamber
                bill_action["action_date"] = action_date
                bill_action["action_type"] = action_type
                bill_actions.append(bill_action)

                # Try to extract vote
                # bill = self.extract_vote_from_action(bill, bill_action, current_chamber, row)

            # if there's a second table, toggle the current chamber
            if current_chamber == "upper":
                current_chamber = "lower"
            else:
                current_chamber = "upper"

        # Add acctions to bill
        for action in bill_actions:
            act = bill.add_action(
                action["action_text"],
                action["action_date"],
                chamber=action["action_chamber"],
                classification=action["action_type"],
            )

            if "committees" in action:
                committee = action["committees"]
                act.add_related_entity(committee, "organization")

        return bill

    def extract_sponsors(self, bill, doc, chamber):
        """
        Extracts sponsors from bill page.
        """
        sponsors = doc.xpath('//div[@class="author"]/ul/li/a/text()')
        for index, sponsor in enumerate(sponsors):
            if index == 0:
                sponsor_type = "primary"
                is_primary = True
            else:
                sponsor_type = "cosponsor"
                is_primary = False

            sponsor_name = sponsor.strip()
            bill.add_sponsorship(
                sponsor_name,
                classification=sponsor_type,
                entity_type="person",
                primary=is_primary,
            )

        return bill

    def extract_versions(self, bill, doc, chamber, version_list_url):
        """
        Versions of a bill are on a separate page, linked to from the column
        labeled, "Bill Text", on the search results page.
        """
        try:
            version_resp = self.get(version_list_url)
        except scrapelib.HTTPError:
            self.warning("Bad version URL detected: {}".format(version_list_url))
            return bill

        version_html = version_resp.text
        if "resolution" in version_resp.url:
            bill.add_version_link(
                "resolution text", version_resp.url, media_type="text/html"
            )
        else:
            version_doc = lxml.html.fromstring(version_html)
            for v in version_doc.xpath('//a[starts-with(@href, "text.php")]'):
                version_url = urllib.parse.urljoin(VERSION_URL_BASE, v.get("href"))
                if "pdf" not in version_url:
                    bill.add_version_link(
                        v.text.strip(),
                        version_url,
                        media_type="text/html",
                        on_duplicate="ignore",
                    )

        return bill

    # def extract_vote_from_action(self, bill, action, chamber, action_row):
    #     """
    #     Gets vote data.  For the Senate, we can only get yes and no
    #     counts, but for the House, we can get details on who voted
    #     what.

    #     TODO: Follow links for Houses and get votes for individuals.
    #     Above todo done in votes.py
    #     """

    #     # Check if there is vote at all
    #     has_vote = action_row.xpath('td/span[contains(text(), "vote:")]')
    #     if len(has_vote) > 0:
    #         vote_element = has_vote[0]
    #         parts = re.match(r'vote:\s+([0-9]*)-([0-9]*)', vote_element.text_content())
    #         if parts is not None:
    #             yeas = int(parts.group(1))
    #             nays = int(parts.group(2))

    #             # Check for URL
    #             vote_url = None
    #             if len(vote_element.xpath('a[@href]')) > 0:
    #                 vote_url = vote_element.xpath('a[@href]')[0].get('href')

    #             # Vote found
    #             # vote = Vote(chamber, action['action_date'],
    #             #     action['action_text'], yeas > nays, yeas, nays, 0)
    #             # # Add source
    #             # if vote_url is not None:
    #             #     vote.add_source(vote_url)
    #             # # Attach to bill
    #             # bill.add_vote(vote)

    #     return bill

    def make_bill_id(self, bill):
        """
        Given a string, ensure that it is in a consistent format.  Bills
        can be written as HF 123, HF123, or HF0123.

        Historically, HF 123 has been used for top level bill id.
        (HF0123 is a better id and should be considered in the future)
        """
        if bill is None:
            return bill

        return re.sub(r"(\w+?)0*(\d+)", r"\1 \2", bill)

    def chamber_from_bill(self, bill):
        """
        Given a bill id, determine chamber.
        """
        if bill is None:
            return bill

        return "lower" if bill.lower().startswith("hf") else "upper"

    def other_chamber(self, chamber):
        """
        Given a chamber, get the other.
        """
        return "lower" if chamber == "upper" else "upper"

    def search_chamber(self, chamber):
        """
        Given chamber, like lower, make into MN site friendly search chamber.
        """
        return {"lower": "House", "upper": "Senate"}[chamber]

    def search_session(self, session):
        """
        Given session ID, make into MN site friendly search.
        """
        return SITE_IDS[session]

    def is_testing(self):
        """
        Determine if this is test mode.
        """
        return False if self.testing is False or self.testing is None else True
