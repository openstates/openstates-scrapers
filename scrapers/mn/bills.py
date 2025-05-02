import re
import datetime
import urllib.parse
import lxml.html
from collections import defaultdict
from io import BytesIO

from openstates.scrape import Scraper, Bill, VoteEvent as Vote

from utils import LXMLMixin

import fitz
import requests
from urllib3.exceptions import InsecureRequestWarning


requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

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
    "2020s1": "1912020",
    "2020s2": "2912020",
    "2020s3": "3912020",
    "2020s4": "4912020",
    "2020s5": "5912020",
    "2020s6": "6912020",
    "2020s7": "7912020",
    "2021-2022": "0922021",
    "2021s1": "1922021",
    "2023-2024": "0932023",
    "2025-2026": "0942025",
}

version_re = re.compile(r".+,\s+(.+):.+Session.+\)\s+Posted on\s+(.+)")


def ensure_url_fully_qualified(url):
    if "http" not in url:
        url = "https://www.senate.mn" + url
    return url


class MNBillScraper(Scraper, LXMLMixin):
    # For testing purposes, this will do a lite version of things.  If
    # testing_bills is set, only these bills will be scraped.  Use SF0077
    testing = True
    testing_bills = ["HF2184"]
    testing_year = "2025"

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

        chambers = [chamber] if chamber else ["upper", "lower"]
        for chamber in chambers:
            # Get bill topics for matching later
            self.get_bill_topics(chamber, session)

            # If testing and certain bills to test, only test those
            if self.is_testing() and len(self.testing_bills) > 0:
                for b in self.testing_bills:
                    bill_url = BILL_DETAIL_URL % (
                        self.search_chamber(chamber),
                        b,
                        self.testing_year,
                    )
                    version_url = VERSION_URL % (
                        self.search_session(session)[-4:],
                        self.search_session(session)[0],
                        b,
                    )
                    yield self.get_bill_info(chamber, session, bill_url, version_url)
                return
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
                html = self.get(url, verify=False).text
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
            # strip leading zeroes from bill number, because that can cause 404s
            bill["version_url"] = VERSION_URL % (
                search_session[-4:],
                search_session[0],
                re.sub(
                    r"([a-zA-Z]+)(0+)([1-9]+)",
                    r"\1\3",
                    bill_details_link.text_content(),
                ),  # SF0120 => SF120
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

        bill = self.extract_companion(bill, doc, session)

        # Grab sponsors
        bill = self.extract_sponsors(bill, doc, chamber)

        # Add Actions performed on the bill.
        bill, votes = self.extract_actions(bill, doc)

        bill = self.extract_versions(bill, doc)

        bill = self.extract_citations(bill, doc)

        for vote in votes:
            yield vote

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
        html = self.get(url, verify=False).text
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
            opt_html = self.get(opt_url, verify=False).text
            opt_doc = lxml.html.fromstring(opt_html)
            for bill in opt_doc.xpath("//table/tbody/tr/td[2]/a/text()"):
                bill = self.make_bill_id(bill)
                self._subject_mapping[bill].append(subject)

    # if a date isn't found in the actions table,
    # check the action text itself
    def parse_inline_action_date(self, text):
        inline_date = re.findall(r"\d{2}/\d{2}/\d+", text, re.MULTILINE)
        if inline_date:
            return inline_date[0]
        return False

    # action date formats are inconsistent
    def parse_dates(self, datestr):
        # Fixing a typo in source data on following URL
        # https://www.revisor.mn.gov/bills/bill.php?b=House&f=HF2184&ssn=0&y=2025
        datestr = datestr.replace("/225", "/2025")
        date_formats = ["%m/%d/%Y", "%m/%d/%y"]
        for fmt in date_formats:
            try:
                return datetime.datetime.strptime(datestr, fmt).date()
            except ValueError:
                pass

        raise ValueError("'%s' is not a recognized date/time" % datestr)

    def extract_actions(self, bill, doc):
        """
        Extract the actions taken on a bill.
        A bill can have actions taken from either chamber.  The current
        chamber's actions will be the first table of actions. The other
        chamber's actions will be in the second table.
        """
        votes = []
        bill_actions = []
        for chamber in ["house", "senate"]:
            tables = doc.cssselect(f".{chamber} table.actions")
            current_chamber_type = "upper" if chamber == "senate" else "lower"
            if len(tables) > 0:
                chamber_actions, chamber_votes = self.process_actions_table(
                    bill, tables[0], current_chamber_type
                )
                bill_actions = bill_actions + chamber_actions
                votes = votes + chamber_votes

        # action_tables = doc.xpath('//table[contains(@class,"actions")]')

        # Add actions to bill
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

        return bill, votes

    def process_actions_table(self, bill: Bill, cur_table, current_chamber):
        votes = list()
        pages = list()
        bill_actions = list()
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
            # Remove large whitespace blocks
            action_text = re.sub(r"\s+", " ", action_text)

            committee = the_rest.xpath("a[contains(@href,'committee')]/text()")
            extra = "".join(the_rest.xpath("span[not(@style)]/text() | a/text()"))
            # skip non-actions (don't have date)
            if action_text in ("Chapter number", "See also", "See"):
                continue
            if action_date:
                action_date = self.parse_dates(action_date)
            else:
                inline_date = self.parse_inline_action_date(action_text)
                if inline_date:
                    action_date = self.parse_dates(inline_date)
                else:
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

            # see if there is a link to a journal page in this action item
            # sometimes a vote has no link, and the relevant page is the previously-mentioned page
            page_links = row.xpath(
                'td//div[contains(@class, "action_item")]//a[contains(@href,"gotopage")]/@href'
            )
            if len(page_links) > 1:
                raise Exception(
                    f"{bill.identifier}: Unexpectedly have multiple page links in a single action"
                )
            elif len(page_links) > 0:
                pages.append(page_links[0])

            # TODO: add votes back in once not broken
            # Try to extract vote
            # senate vote only, house votes are scraped by the vote_event.py scraper
            # if current_chamber == "upper":
            #     vote = self.extract_vote_from_action(
            #         bill, bill_action, current_chamber, row, pages
            #     )
            #     if vote:
            #         votes.append(vote)

        return bill_actions, votes

    # MN provides data in two parts,
    # the session law (or chaptered law), which makes the list of changes legal until a new code is printed
    # and all the various parts of the code that are getting amended by the given bill.
    def extract_citations(self, bill, bill_doc):
        for link in bill_doc.xpath(
            '//div[contains(string(.), "Session Law Chapter") and a[contains(@href,"/laws")]]/a'
        ):
            cite_url = link.xpath("@href")[0]
            chapter = link.xpath("text()")[0]
            html = self.get(cite_url, verify=False).text
            doc = lxml.html.fromstring(html)

            title = doc.xpath(
                "string(//div[contains(@class,'col-12 col-md-8')]/h1)"
            ).strip()
            bill.add_citation(
                title,
                f"Chapter {chapter}",
                citation_type="chapter",
                url=cite_url,
            )

            amends = self.get_nodes(
                doc,
                "//h1[contains(@class,'bill_sec_header') and contains(text(),'is amended')]",
            )
            for amend in amends:
                full_cite = amend.xpath("text()")[0]
                cite_parts = full_cite.split(",")
                bill.add_citation(
                    cite_parts[0].strip(),
                    "".join(cite_parts[1:-1]).strip(),
                    citation_type="final",
                    url=cite_url,
                )
        return bill

    def extract_companion(self, bill, doc, session):
        companion = doc.xpath(
            "//div[contains(text(), 'Companion:') and not(contains(text(), 'None'))]/a[1]"
        )

        if not companion:
            return bill

        bill_id = self.make_bill_id(companion[0].xpath("text()")[0])
        if companion:
            bill.add_related_bill(
                identifier=bill_id,
                legislative_session=session,
                relation_type="companion",
            )
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

    # Senate Resolution text server is throwing weird HTTP errors at urls like:
    # https://www.revisor.mn.gov/bills/text.php?number=SC9&version=latest&session=ls93&session_year=2024&session_number=0
    # that url normally just does a redirect to another url, anyway
    # so this func rewrites to the final URL that a normal browser arrives at
    def rewrite_senate_resolution_url(self, url):
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        # check that we have expected params in the incoming URL
        if not all(
            k in params for k in ("session", "number", "session_number", "session_year")
        ):
            self.logger.error(
                f"Tried to rewrite senate URL but missing expected params in {url}"
            )
            return url

        bill_num_parts = re.search(r"([A-Z]+)([0-9]+)", params["number"][0])
        new_url_base = "https://www.senate.mn/resolutions/display_resolution.html?"
        new_params = {
            "ls": params["session"][0].replace("ls", ""),
            "bill_type": bill_num_parts[1],
            "bill_number": bill_num_parts[2],
            "ss_number": params["session_number"][0],
            "ss_year": params["session_year"][0],
        }
        new_query = "&".join([f"{key}={new_params[key]}" for key in new_params])
        new_url = f"{new_url_base}{new_query}"
        return new_url

    def extract_versions(self, bill, doc):
        # Get all versions of the bill.
        version_rows = doc.xpath("//div[@id='versions']/table/tr[td]")

        # If there is NOT a 'Version List' expander to show versions table,
        #  this gets versions from link on page that follows the label
        #  "Current bill text:"
        if not version_rows:
            try:
                current = doc.xpath(
                    "//div[contains(text(), 'Current bill text')]/a[1]"
                )[0]
                current_html_url = current.xpath("@href")[0]
                # if senate resolution, rewrite URL to avoid weird HTTP server errros
                if (
                    "https://www.revisor.mn.gov/bills/text.php" in current_html_url
                    and (
                        "sc" in bill.identifier.lower()
                        or "sr" in bill.identifier.lower()
                    )
                ):
                    current_html_url = self.rewrite_senate_resolution_url(
                        current_html_url
                    )
                current_response = requests.get(current_html_url, verify=False)
                current_content = lxml.html.fromstring(current_response.content)

                pdf_xpath = ".//a[contains(text(), 'Authors and Status')]/../following-sibling::td/a"

                current_pdf_url = current_content.xpath(pdf_xpath)[0].xpath("@href")[0]
                current_pdf_url = ensure_url_fully_qualified(current_pdf_url)

                vers_list = [
                    x
                    for x in current_content.xpath(".//b")
                    if "Posted on" in x.getparent().text_content()
                ]

                for vers in vers_list:
                    vers_descriptor = vers.getparent().text_content().strip()
                    title_date_match = version_re.search(vers_descriptor)
                    if not title_date_match:
                        continue
                    raw_title, raw_date = title_date_match.groups()
                    vers_title = (
                        "Introduction"
                        if "introduced" in raw_title.lower()
                        else raw_title
                    )
                    vers_day = datetime.datetime.strptime(raw_date, "%B %d, %Y").date()

                    href = vers.getparent().xpath("@href")
                    # If parent element has href, that means it is a link
                    # to an additional version, and the below conditional block
                    # gets the html and pdf urls for that version
                    if href:
                        vers_html_url = href[0]
                        vers_html_url = ensure_url_fully_qualified(vers_html_url)
                        vers_response = requests.get(vers_html_url, verify=False)
                        vers_content = lxml.html.fromstring(vers_response.content)
                        vers_pdf_url = vers_content.xpath(pdf_xpath)[0].xpath("@href")[
                            0
                        ]
                        vers_pdf_url = ensure_url_fully_qualified(vers_pdf_url)

                    # If parent element does not have href, it is current version
                    else:
                        vers_html_url = current_html_url
                        vers_pdf_url = current_pdf_url

                    bill.add_version_link(
                        vers_title,
                        vers_html_url,
                        date=vers_day,
                        media_type="text/html",
                        on_duplicate="ignore",
                    )
                    bill.add_version_link(
                        vers_title,
                        vers_pdf_url,
                        date=vers_day,
                        media_type="application/pdf",
                        on_duplicate="ignore",
                    )

            except IndexError:
                self.warning(f"No versions were found for {bill.identifier}")

        # Otherwise if there IS a 'Version List' to show versions table
        for row in version_rows:
            html_link = row.xpath("td[1]/a")[0]
            version_title = html_link.text_content().strip().replace("  ", " ")
            version_day = row.xpath("td[3]/text()")[0].strip()
            version_day = version_day.replace("Posted on", "").strip()
            version_day = datetime.datetime.strptime(version_day, "%m/%d/%Y").date()
            html_url = html_link.xpath("@href")[0]
            bill.add_version_link(
                version_title,
                html_url,
                date=version_day,
                media_type="text/html",
                on_duplicate="ignore",
            )
            if row.xpath("td[2]/a[@aria-label='PDF document']"):
                pdf_url = row.xpath("td[2]/a[@aria-label='PDF document']/@href")[0]
                bill.add_version_link(
                    version_title,
                    pdf_url,
                    date=version_day,
                    media_type="application/pdf",
                    on_duplicate="ignore",
                )

        return bill

    def extract_vote_from_action(self, bill, action, chamber, action_row, pages):
        """
        Gets vote data.  For the Senate, we can only get yes and no
        counts, but for the House, we can get details on who voted
        what.
        For only Senate vote.
        For House vote, refer to vote_events.py.
        """
        # Check if there is vote at all
        has_vote = action_row.xpath(
            'td//div[contains(@class, "action_item")][contains(., "vote")]'
        )
        if len(has_vote) > 0:
            vote_element = has_vote[0]
            parts = re.search(
                r"vote:\s+([0-9]*)-([0-9]*)",
                vote_element.text_content(),
                flags=re.M | re.U,
            )
            if parts is not None:
                yeas = int(parts.group(1))
                nays = int(parts.group(2))
                # Check for URL
                vote_date = action["action_date"]
                if not vote_element.xpath(".//a[@href]/@href"):
                    # in this case, use the previous vote url
                    vote_url = pages[-1]
                    self.warning(
                        f"No vote url in the page. trying to use the previous vote url: {vote_url}"
                    )
                    if not vote_url:
                        return [None] * 2
                else:
                    vote_url = vote_element.xpath(".//a[@href]/@href")[0]

                vote_url_obj = urllib.parse.urlparse(vote_url)
                vote_url_qs = urllib.parse.parse_qs(vote_url_obj.query)
                session = vote_url_qs["session"][0].replace("ls", "")
                number = re.sub("[^0-9]", "", vote_url_qs["number"][0])
                vote_pdf_api = f"https://www.senate.mn/api/journal/gotopage?page={number}&ls={session}"
                vote_pdf_res = self.get(vote_pdf_api).json()
                page_number = vote_pdf_res["internal_page"]
                filename = vote_pdf_res["filename"]
                biennium = vote_pdf_res["fileBiennium"]
                pdf_url = f"https://www.senate.mn/journals/{biennium}/{filename}.pdf"

                # Vote found
                vote = Vote(
                    chamber=chamber,
                    start_date=vote_date,
                    motion_text=action["action_text"],
                    result="pass" if yeas > nays else "fail",
                    bill=bill,
                    classification="passage",
                )
                vote.add_source(f"{pdf_url}#{page_number}")
                vote.set_count("yes", yeas)
                vote.set_count("no", nays)

                pdf_response = self.get(pdf_url)
                doc = fitz.open("pdf", BytesIO(pdf_response.content))

                first_page = max(0, page_number - 2)
                last_page = min(page_number, doc.page_count - 1)

                page = "\n".join(
                    [
                        doc[p].get_text()
                        for p in range(
                            first_page,
                            last_page + 1,
                        )
                        if not doc.is_closed
                    ]
                )
                page = page.replace("\u200b", "")
                yes_voters = []
                no_voters = []

                wait_yes = False
                seen_yes = False
                wait_no = False
                seen_no = False

                for line in page.splitlines():
                    if (
                        re.match(r"^\d+$", line)
                        or "DAY" in line
                        or "SENATE" in line
                        or not line
                    ):
                        continue
                    if seen_yes:
                        if len(line.split(" ")) > 2 or len(yes_voters) == yeas:
                            seen_yes = False
                            wait_no = True
                        else:
                            yes_voters.append(line)
                    if seen_no:
                        if len(line.split(" ")) > 2 or len(no_voters) == nays:
                            seen_no = False
                            break
                        else:
                            no_voters.append(line)

                    if f"yeas {yeas} and nays {nays}" in line:
                        wait_yes = True
                        continue
                    elif yeas == 0 and wait_yes:
                        wait_no = True
                        continue
                    elif "Those who voted in the affirmative were" in line and wait_yes:
                        seen_yes = True
                        continue
                    elif nays == 0 and wait_no:
                        break
                    elif "Those who voted in the negative were" in line and wait_no:
                        seen_no = True
                        continue

                if (len(yes_voters) == yeas) and (len(no_voters) == nays):
                    for line in yes_voters:
                        vote.yes(line)
                    for line in no_voters:
                        vote.no(line)
                else:
                    self.warning(
                        f"{vote.bill_identifier}: Inconsistent between vote number and length of voters: {yeas}: {nays} \n {yes_voters} \n {no_voters}"
                    )
                # # Attach to bill
                return vote

        return None

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
