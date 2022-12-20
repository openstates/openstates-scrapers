import dateutil
import re
import scrapelib
import os
from collections import defaultdict
from pytz import timezone
from datetime import datetime
from openstates.scrape import Scraper, Bill, VoteEvent
from openstates.utils import convert_pdf
from utils import LXMLMixin
from utils.media import get_media_type

import pytz
import math

central = pytz.timezone("US/Central")


def chamber_abbr(chamber):
    if chamber == "upper":
        return "S"
    else:
        return "H"


def session_url(session):
    return "https://apps.legislature.ky.gov/record/%s/" % session[2:]


class KYBillScraper(Scraper, LXMLMixin):
    _TZ = timezone("America/Kentucky/Louisville")
    _subjects = defaultdict(list)
    _is_post_2016 = False

    _action_classifiers = [
        ("introduced in", "introduction"),
        ("signed by Governor", ["executive-signature"]),
        ("vetoed", "executive-veto"),
        (r"^to [A-Z]", "referral-committee"),
        (" to [A-Z]", "referral-committee"),
        ("reported favorably", "committee-passage"),
        ("adopted by voice vote", "passage"),
        ("3rd reading, passed", ["reading-3", "passage"]),
        ("1st reading", "reading-1"),
        ("2nd reading", "reading-2"),
        ("3rd reading", "reading-3"),
        ("passed", "passage"),
        (r"bill passed", "passage"),
        ("line items vetoed", "executive-veto-line-item"),
        ("delivered to secretary of state", "became-law"),
        ("became law without", "became-law"),
        ("veto overridden", "veto-override-passage"),
        ("adopted by voice vote", "passage"),
        (
            r"floor amendments?( \([a-z\d\-]+\))*" r"( and \([a-z\d\-]+\))? filed",
            "amendment-introduction",
        ),
        ("enrolled, signed by", "passage"),
    ]

    def classify_action(self, action):
        for regex, classification in self._action_classifiers:
            if re.match(regex, action, re.IGNORECASE):
                return classification
        return None

    def scrape(self, session=None, chamber=None, prefiles=None):
        # Bill page markup changed starting with the 2016 regular session.
        # kinda gross
        if int(session[0:4]) >= 2016:
            self._is_post_2016 = True

        if prefiles is not None:
            yield from self.scrape_prefiles(session)
        else:
            # self.scrape_subjects(session)
            chambers = [chamber] if chamber else ["upper", "lower"]
            for chamber in chambers:
                yield from self.scrape_session(chamber, session)

    def scrape_prefiles(self, session):
        prefile_url = (
            "https://apps.legislature.ky.gov/record/{}/prefiled/prefiled_bills.html"
        )
        prefile_url = prefile_url.format(session[-4:].lower())
        page = self.lxmlize(prefile_url)

        for link in page.xpath("//div[contains(@class,'container')]/p/a"):
            if re.search(r"\d{1,4}\.htm", link.attrib.get("href", "")):
                bill_id = link.text
                bill_id = "BR" + bill_id
                self.info(bill_id)
                yield from self.parse_bill(
                    "upper", session, bill_id, link.attrib["href"]
                )

    def scrape_session(self, chamber, session):
        chamber_map = {"upper": "senate", "lower": "house"}
        bill_url = session_url(session) + "%s_bills.html" % chamber_map[chamber]
        yield from self.scrape_bill_list(chamber, session, bill_url)

        resolution_url = (
            session_url(session) + "%s_resolutions.html" % chamber_map[chamber]
        )
        yield from self.scrape_bill_list(chamber, session, resolution_url)

    def scrape_bill_list(self, chamber, session, url):
        bill_abbr = None
        page = self.lxmlize(url)

        for link in page.xpath("//div[contains(@class,'container')]/p/a"):
            if re.search(r"\d{1,4}\.htm", link.attrib.get("href", "")):
                bill_id = link.text
                match = re.match(
                    r".*\/([a-z]+)([\d]+)\.html", link.attrib.get("href", "")
                )
                if match:
                    bill_abbr = match.group(1)
                    bill_id = bill_abbr.upper() + bill_id.replace(" ", "")
                else:
                    bill_id = bill_abbr.upper() + bill_id

                yield from self.parse_bill(
                    chamber, session, bill_id, link.attrib["href"]
                )

    def parse_actions(self, page, bill, chamber):
        # //div[preceding-sibling::a[@id="actions"]]
        action_rows = page.xpath(
            '//div[preceding-sibling::a[@id="actions"]][1]/table[1]/tbody/tr'
        )
        for row in action_rows:
            action_date = row.xpath("th[1]/text()")[0].strip()

            action_date = datetime.strptime(action_date, "%m/%d/%y")
            action_date = self._TZ.localize(action_date)

            action_texts = row.xpath("td[1]/ul/li/text() | td[1]/ul/li/strong/text()")

            for action_text in action_texts:
                action_text = action_text.strip()
                if action_text.endswith("House") or action_text.endswith("(H)"):
                    actor = "lower"
                elif action_text.endswith("Senate") or action_text.endswith("(S)"):
                    actor = "upper"
                else:
                    actor = chamber

                classifications = self.classify_action(action_text)
                bill.add_action(
                    action_text,
                    action_date,
                    chamber=actor,
                    classification=classifications,
                )

    # Get the field to the right for a given table header
    def parse_bill_field(self, page, header):
        xpath_expr = '//tr[th[text()="{}"]]/td[1]'.format(header)
        if page.xpath(xpath_expr):
            return page.xpath(xpath_expr)[0]
        else:
            return ""

    def parse_bill(self, chamber, session, bill_id, url):
        try:
            page = self.lxmlize(url)
        except scrapelib.HTTPError as e:
            self.logger.warning(e)
            return

        withdrawn = False

        if self.parse_bill_field(page, "Last Action") != "":
            last_action = self.parse_bill_field(page, "Last Action").xpath("text()")[0]
            if "WITHDRAWN" in last_action.upper():
                self.info("{} Withdrawn, skipping".format(bill_id))
                withdrawn = True

        if withdrawn:
            title = "Withdrawn."
        else:
            title = self.parse_bill_field(page, "Title").text_content()

        if "CR" in bill_id:
            bill_type = "concurrent resolution"
        elif "JR" in bill_id:
            bill_type = "joint resolution"
        elif "R" in bill_id:
            bill_type = "resolution"
        else:
            bill_type = "bill"

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=title,
            classification=bill_type,
        )
        bill.subject = self._subjects[bill_id]
        bill.add_source(url)

        self.parse_versions(page, bill)

        self.parse_actions(page, bill, chamber)
        self.parse_subjects(page, bill)
        self.parse_proposed_amendments(page, bill)

        # LM is "Locally Mandated fiscal impact"
        fiscal_notes = page.xpath('//a[contains(@href, "/LM.pdf")]')
        for fiscal_note in fiscal_notes:
            source_url = fiscal_note.attrib["href"]
            mimetype = get_media_type(source_url)

            bill.add_document_link("Fiscal Note", source_url, media_type=mimetype)

        # only grab links in the first table, because proposed amendments have sponsors that are not bill sponsors.
        for link in page.xpath(
            "//div[contains(@class,'bill-table')][1]//td/span/a[contains(@href, 'Legislator-Profile')]"
        ):
            bill.add_sponsorship(
                link.text.strip(),
                classification="primary",
                entity_type="person",
                primary=True,
            )

        if page.xpath("//th[contains(text(),'Votes')]"):
            vote_url = page.xpath("//a[contains(text(),'Vote History')]/@href")[0]
            yield from self.scrape_votes(vote_url, bill, chamber)

        bdr_no = self.parse_bill_field(page, "Bill Request Number")
        if bdr_no != "" and bdr_no.xpath("text()"):
            bdr = bdr_no.xpath("text()")[0].strip()
            bill.extras["BDR"] = bdr

        if self.parse_bill_field(page, "Summary of Original Version") != "":
            summary = (
                self.parse_bill_field(page, "Summary of Original Version")
                .text_content()
                .strip()
            )
            bill.add_abstract(summary, note="Summary of Original Version")

        if withdrawn:
            action = self.parse_bill_field(page, "Last Action").text_content().strip()
            wd_date = re.findall(r"\d{2}\/\d{2}\/\d+", action)[0]
            wd_date = dateutil.parser.parse(wd_date).date()
            bill.add_action(
                action, wd_date, chamber=chamber, classification="withdrawal"
            )

        yield bill

    def parse_versions(self, page, bill):
        xpath_expr = '//tr[th[text()="Bill Documents"]]/td[1]/a'
        version_count = 0
        for row in page.xpath(xpath_expr):
            source_url = row.attrib["href"]
            version_title = row.xpath("text()")[0].strip()

            mimetype = get_media_type(source_url)
            if mimetype is None:
                self.warning("Unknown mimetype for {}".format(source_url))

            bill.add_version_link(version_title, source_url, media_type=mimetype)
            version_count += 1
        return version_count

    def parse_proposed_amendments(self, page, bill):
        # div.bill-table with an H4 "Proposed Amendments", all a's in the first TD of the first TR
        # that point to a path including "recorddocuments"
        xpath = (
            '//div[contains(@class, "bill-table") and descendant::h4[text()="Proposed Amendments"]]'
            '//tr[1]/td[1]/a[contains(@href,"recorddocuments")]'
        )

        for link in page.xpath(xpath):
            note = link.xpath("text()")[0].strip()
            note = "Proposed {}".format(note)
            url = link.attrib["href"]
            bill.add_document_link(note=note, url=url)

    def scrape_votes(self, vote_url, bill, chamber):

        try:
            filename, response = self.urlretrieve(vote_url)
        except scrapelib.HTTPError:
            self.logger.warning("PDF not posted or available")
            return
        # Grabs text from pdf
        pdflines = [
            line.decode("utf-8") for line in convert_pdf(filename, "text").splitlines()
        ]
        os.remove(filename)

        vote_date = 0
        voters = defaultdict(list)
        for x in range(len(pdflines)):
            line = pdflines[x]
            if re.search(r"(\d+/\d+/\d+)", line):
                initial_date = line.strip()
            if ("AM" in line) or ("PM" in line):
                split_l = line.split()
                for y in split_l:
                    if ":" in y:
                        time_location = split_l.index(y)
                        motion = " ".join(split_l[0:time_location])
                        time = split_l[time_location:]
                        if len(time) > 0:
                            time = "".join(time)
                        dt = initial_date + " " + time
                        dt = datetime.strptime(dt, "%m/%d/%Y %I:%M:%S%p")
                        vote_date = central.localize(dt)
                        vote_date = vote_date.isoformat()
                        # In rare case that no motion is provided
                        if len(motion) < 1:
                            motion = "No Motion Provided"
            if "YEAS:" in line:
                yeas = int(line.split()[-1])
            if "NAYS:" in line:
                nays = int(line.split()[-1])
            if "ABSTAINED:" in line:
                abstained = int(line.split()[-1])
            if "PASSES:" in line:
                abstained = int(line.split()[-1])
            if "NOT VOTING:" in line:
                not_voting = int(line.split()[-1])

            if "YEAS :" in line:
                y = 0
                next_line = pdflines[x + y]
                while "NAYS : " not in next_line:
                    next_line = next_line.split("  ")
                    if next_line and ("YEAS" not in next_line):
                        for v in next_line:
                            if v and "YEAS" not in v:
                                voters["yes"].append(v.strip())
                    next_line = pdflines[x + y]
                    y += 1
            if line and "NAYS :" in line:
                y = 0
                next_line = 0
                next_line = pdflines[x + y]
                while ("ABSTAINED : " not in next_line) and (
                    "PASSES :" not in next_line
                ):
                    next_line = next_line.split("  ")
                    if next_line and "NAYS" not in next_line:
                        for v in next_line:
                            if v and "NAYS" not in v:
                                voters["no"].append(v.strip())
                    next_line = pdflines[x + y]
                    y += 1

            if line and ("ABSTAINED :" in line or "PASSES :" in line):
                y = 2
                next_line = 0
                next_line = pdflines[x + y]
                while "NOT VOTING :" not in next_line:
                    next_line = next_line.split("  ")
                    if next_line and (
                        "ABSTAINED" not in next_line or "PASSES" not in next_line
                    ):
                        for v in next_line:
                            if v:
                                voters["abstain"].append(v.strip())
                    next_line = pdflines[x + y]
                    y += 1

            if line and "NOT VOTING : " in line:
                lines_to_go_through = math.ceil(not_voting / len(line.split()))
                next_line = pdflines[x]
                for y in range(lines_to_go_through):
                    if len(pdflines) > (x + y + 2):
                        next_line = pdflines[x + y + 2].split("  ")
                        for v in next_line:
                            if v:
                                voters["not voting"].append(v.strip())
                if yeas > (nays + abstained + not_voting):
                    passed = True
                else:
                    passed = False

                ve = VoteEvent(
                    chamber=chamber,
                    start_date=vote_date,
                    motion_text=motion,
                    result="pass" if passed else "fail",
                    bill=bill,
                    classification="passage",
                )
                ve.add_source(vote_url)
                for how_voted, how_voted_voters in voters.items():
                    for voter in how_voted_voters:
                        if len(voter) > 0:
                            ve.vote(how_voted, voter)
                # Resets voters dictionary before going onto next page in pdf
                voters = defaultdict(list)
                yield ve

    def parse_subjects(self, page, bill):
        if self.parse_bill_field(page, "Index Headings of Original Version") == "":
            return
        subject_div = self.parse_bill_field(page, "Index Headings of Original Version")
        subjects = subject_div.xpath("a/text()")
        seen_subjects = []
        for subject in subjects:
            if subject not in seen_subjects:
                bill.add_subject(subject.strip())
                seen_subjects.append(subject)
