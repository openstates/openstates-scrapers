import re
import datetime as dt
from collections import defaultdict

import pytz

import lxml.html

from openstates.scrape import Scraper, Bill, VoteEvent as Vote
from .actions import Categorizer

from .legacyBills import NHLegacyBillScraper

import feedparser

body_code = {"lower": "H", "upper": "S"}
chamber_map = {
    "H": "lower",
    "S": "upper",
    "C": "legislature",
}
bill_type_map = {
    "B": "bill",
    "R": "resolution",
    "CR": "concurrent resolution",
    "JR": "joint resolution",
    "CO": "concurrent order",
    "A": "bill of address",
    # special session senate/house bill
    "SSSB": "bill",
    "SSHB": "bill",
}

extended_type_map = {
    "HB": "bill",
    "SB": "bill",
    "HCR": "concurrent resolution",
    "SCR": "concurrent resolution",
    "HR": "resolution",
    "SR": "resolutoin",
    "JR": "resolution",
    "HJR": "joint resolution",
    "SJR": "joint resolution",
    "HCO": "concurrent order",
    "SCO": "concurrent order",
    "CO": "concurrent order",
    "SSSB": "bill",
    "SSHB": "bill",
    "CACR": "constitutional amendment",
    "PET": "petition,",
}

VERSION_URL = "https://gc.nh.gov/legislation/%s/%s.html"
AMENDMENT_URL = "https://gc.nh.gov/legislation/amendments/%s.html"


def extract_amendment_id(action):
    piece = re.findall(r"Amendment #(\d{4}-\d+[hs])", action)
    if piece:
        return piece[0]


class NHBillScraper(Scraper):
    cachebreaker = dt.datetime.now().strftime("%Y%d%d%H%I%s")
    categorizer = Categorizer()

    def scrape(self, chamber=None, session=None, scrape_from_web=None):
        est = pytz.timezone("America/New_York")
        time_est = dt.datetime.now(est)

        if time_est.hour > 6 and time_est.hour < 21:
            self.warning("NH bans scraping between 6am and 9pm. This may fail.")

        chambers = [chamber] if chamber else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session, scrape_from_web)

    def scrape_from_web(self, session):
        bills = {}

        url = f"https://gc.nh.gov/rssFeeds/rssQueryResults.aspx?&sortoption=&txtsessionyear={session}"
        feed = self.get(url).content
        feed = feedparser.parse(feed)

        for item in feed.entries:
            # Uncomment below to debug scrape of a specific bill
            # if "HB323" not in item["title"]:
            #     continue
            bill_type = self.extract_until_number(item.billnumber)
            bill_type = extended_type_map[bill_type]

            bill_id = item.billnumber
            lsr = item.lsrnumber
            # Pad lsr with zeroes so that it is a 4-character string
            # lsr value is a padding string in the bulk data documents that are parsed elsewhere, so needs to match
            lsr = lsr.zfill(4)

            bills[lsr] = Bill(
                legislative_session=session,
                chamber=chamber_map[item.billnumber[0:1]],
                identifier=bill_id,
                title=item.lsrtitle.replace("\n", ""),
                classification=bill_type,
            )

            if lsr not in self.versions_by_lsr:
                # Try to get the bill versions from the bill page
                # since no version was found in the bulk data (for unknown reason)
                docket_url = f"https://gc.nh.gov/bill_status/legacy/bs2016/bill_docket.aspx?lsr={lsr}&sy={session}&sortoption=&txtsessionyear={session}"
                docket_content = None
                try_num = 1
                tries = 3
                # we have to be prepared to retry, because sometimes NH responds with a basically empty HTML response
                # (contains only some inline Javascript snippet)
                while try_num < tries and (
                    docket_content is None or "<head></head>" in docket_content
                ):
                    if try_num > 1:
                        self.logger.info(
                            f"Retrying fetch of docket page, try number {try_num}"
                        )
                    docket_content = self.get(
                        docket_url,
                        allow_redirects=True,
                        headers={
                            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                        },
                    ).content.decode("utf-8")
                    try_num += 1

                docket_page = lxml.html.fromstring(docket_content)
                version_elems = docket_page.xpath(
                    "//table[@id='Table1']//a[contains(@href, 'billtext.aspx') or contains(@href, 'billText.aspx')]"
                )
                version_urls_seen = []
                for version_elem in version_elems:
                    version_url = version_elem.attrib["href"]
                    if version_url in version_urls_seen:
                        # do not add duplicates
                        continue
                    else:
                        version_urls_seen.append(version_url)
                    version_text = version_elem.xpath(".//text()")[0]
                    if "txtFormat=html" in version_url:
                        # "normal" version (maybe always Introduced?)
                        bills[lsr].add_version_link(
                            note=version_text,
                            url=f"https://gc.nh.gov/bill_status/legacy/bs2016/{version_url}",
                            media_type="text/html",
                        )
                        pdf_version_url = version_url.replace(
                            "txtFormat=html", "txtFormat=pdf"
                        )
                        bills[lsr].add_version_link(
                            note=version_text,
                            url=f"https://gc.nh.gov/bill_status/legacy/bs2016/{pdf_version_url}",
                            media_type="application/pdf",
                        )
                    elif "txtFormat=amend" in version_url:
                        # Amendment version
                        # pretty sure this is always a PDF
                        bills[lsr].add_version_link(
                            note=f"Amendment: {version_text}",
                            url=f"https://gc.nh.gov/bill_status/legacy/bs2016/{version_url}",
                            media_type="application/pdf",
                        )
                    elif "v=HP" in version_url or "v=SP" in version_url:
                        # This is the House Passed or Senate Passed version
                        # pretty sure this is always HTML, but PDF is available
                        bills[lsr].add_version_link(
                            note=version_text,
                            url=f"https://gc.nh.gov/bill_status/legacy/bs2016/{version_url}",
                            media_type="text/html",
                        )
                        pdf_version_url = f"{version_url}&txtFormat=pdf"
                        bills[lsr].add_version_link(
                            note=version_text,
                            url=f"https://gc.nh.gov/bill_status/legacy/bs2016/{pdf_version_url}",
                            media_type="application/pdf",
                        )
                    else:
                        self.logger.warning(
                            f"Found an unexpected version URL on {docket_url}, version URL: {version_url}"
                        )

            if lsr in self.versions_by_lsr:
                version_id = self.versions_by_lsr[lsr]
                version_url = (
                    "https://gc.nh.gov/bill_status/legacy/bs2016/"
                    "billText.aspx?sy={}&id={}&txtFormat=html".format(
                        session, version_id
                    )
                )

                pdf_version_url = (
                    "https://gc.nh.gov/bill_status/legacy/bs2016/"
                    "billText.aspx?sy={}&id={}&txtFormat=pdf&v=current".format(
                        session, version_id
                    )
                )
                latest_version_name = "latest version"
                bills[lsr].add_version_link(
                    note=latest_version_name,
                    url=version_url,
                    media_type="text/html",
                )
                bills[lsr].add_version_link(
                    note=latest_version_name,
                    url=pdf_version_url,
                    media_type="application/pdf",
                )

            self.bills_by_id[bill_id] = bills[lsr]

        return bills

    def scrape_chamber(self, chamber, session, scrape_from_web):
        if int(session) < 2017:
            legacy = NHLegacyBillScraper(self.metadata, self.datadir)
            yield from legacy.scrape(chamber, session)
            # This throws an error because object_count isn't being properly incremented,
            # even though it saves fine. So fake the output_names
            self.output_names = ["1"]
            return

        # bill basics
        self.bills = {}  # LSR->Bill
        self.bills_by_id = {}  # need a second table to attach votes
        self.versions_by_lsr = {}  # mapping of bill ID to lsr
        self.amendments_by_lsr = {}

        # pre load the mapping table of LSR -> version id
        self.scrape_version_ids()
        self.scrape_amendments()

        if scrape_from_web and self.bills == {}:
            self.info("Scraping from web.")
            self.bills = self.scrape_from_web(session)
        else:

            last_line = []
            for line in (
                self.get(
                    f"https://gc.nh.gov/dynamicdatadump/LSRs.txt?x={self.cachebreaker}"
                )
                .content.decode("utf-8")
                .split("\n")
            ):
                # the first line in the file can contain a unicode zero width character \\ufeff
                # maybe found in other lines? so just replace universally
                line = line.replace("\ufeff", "")
                line = line.split("|")
                if len(line) < 1:
                    continue

                if len(line) < 36:
                    if len(last_line + line[1:]) == 36:
                        # combine two lines for processing
                        # (skip an empty entry at beginning of second line)
                        line = last_line + line
                        self.warning("used bad line")
                    else:
                        # skip this line, maybe we'll use it later
                        self.warning("bad line: %s" % "|".join(line))
                        last_line = line
                        continue
                session_yr = line[0]
                lsr = line[1]
                title = line[2]
                body = line[3]
                # type_num = line[4]
                expanded_bill_id = line[9]
                bill_id = line[10]

                if (
                    body == body_code[chamber]
                    and session_yr == session
                    and expanded_bill_id != ""
                ):
                    if expanded_bill_id.startswith("CACR"):
                        bill_type = "constitutional amendment"
                    elif expanded_bill_id.startswith("PET"):
                        bill_type = "petition"
                    elif expanded_bill_id.startswith("AR") and bill_id.startswith(
                        "CACR"
                    ):
                        bill_type = "constitutional amendment"
                    elif expanded_bill_id.startswith(
                        "SSSB"
                    ) or expanded_bill_id.startswith("SSHB"):
                        # special session house/senate bills
                        bill_type = "bill"
                    else:
                        bill_type = bill_type_map[expanded_bill_id.split(" ")[0][1:]]

                    if title.startswith("("):
                        title = title.split(")", 1)[1].strip()

                    self.bills[lsr] = Bill(
                        legislative_session=session,
                        chamber=chamber,
                        identifier=bill_id,
                        title=title,
                        classification=bill_type,
                    )

                    # check to see if resolution, process versions by getting lsr off link on the bill source page
                    if re.match(r"^.R\d+", bill_id):
                        # ex: HR 1 is lsr=847 but version id=838
                        resolution_url = (
                            "https://gc.nh.gov/bill_status/legacy/bs2016/bill_status.aspx?"
                            + "lsr={}&sy={}&txtsessionyear={}&txtbillnumber={}".format(
                                lsr, session, session, bill_id
                            )
                        )
                        resolution_page = self.get(
                            resolution_url, allow_redirects=True
                        ).content.decode("utf-8")
                        page = lxml.html.fromstring(resolution_page)
                        try:
                            version_href = page.xpath("//a[2]/@href")[1]
                        except Exception:
                            self.logger.warning(f"{bill_id} missing version link")
                            continue
                        true_version = re.search(r"id=(\d+)&", version_href)[1]
                        self.versions_by_lsr[lsr] = true_version

                    # http://www.gencourt.state.nh.us/bill_status/billText.aspx?sy=2017&id=95&txtFormat=html
                    # or if 2022 bills
                    # http://www.gencourt.state.nh.us/bill_status/legacy/bs2016/billText.aspx?id=1410&txtFormat=html&sy=2022
                    if lsr in self.versions_by_lsr:
                        version_id = self.versions_by_lsr[lsr]
                        version_url = (
                            "https://gc.nh.gov/bill_status/legacy/bs2016/"
                            "billText.aspx?sy={}&id={}&txtFormat=html".format(
                                session, version_id
                            )
                        )

                        pdf_version_url = (
                            "https://gc.nh.gov/bill_status/legacy/bs2016/"
                            "billText.aspx?sy={}&id={}&txtFormat=pdf&v=current".format(
                                session, version_id
                            )
                        )
                        latest_version_name = "latest version"
                        self.bills[lsr].add_version_link(
                            note=latest_version_name,
                            url=version_url,
                            media_type="text/html",
                        )
                        self.bills[lsr].add_version_link(
                            note=latest_version_name,
                            url=pdf_version_url,
                            media_type="application/pdf",
                        )

                    # http://gencourt.state.nh.us/bill_status/billtext.aspx?sy=2017&txtFormat=amend&id=2017-0464S
                    if lsr in self.amendments_by_lsr:
                        amendment_id = self.amendments_by_lsr[lsr]
                        amendment_url = (
                            "https://gc.nh.gov/bill_status/legacy/bs2016/"
                            "billText.aspx?sy={}&id={}&txtFormat=amend".format(
                                session, amendment_id
                            )
                        )
                        amendment_name = "Amendment #{}".format(amendment_id)

                        self.bills[lsr].add_version_link(
                            note=amendment_name,
                            url=amendment_url,
                            media_type="application/pdf",
                        )

                    self.bills_by_id[bill_id] = self.bills[lsr]

        # load legislators
        self.legislators = {}
        for line in (
            self.get(
                "https://gc.nh.gov/dynamicdatadump/legislators.txt?x={}".format(
                    self.cachebreaker
                )
            )
            .content.decode("utf-8")
            .split("\n")
        ):
            if len(line) < 2:
                continue

            line = line.split("|")
            employee_num = line[0].replace("\ufeff", "")

            # first, last, middle
            if len(line) > 2:
                name = "%s %s %s" % (line[2], line[3], line[1])
            else:
                name = "%s %s" % (line[2], line[1])

            self.legislators[employee_num] = {"name": name, "seat": line[5]}
            # body = line[4]

        # sponsors
        for line in (
            self.get(
                f"https://gc.nh.gov/dynamicdatadump/LsrSponsors.txt?x={self.cachebreaker}"
            )
            .content.decode("utf-8")
            .split("\n")
        ):
            if len(line) < 1:
                continue

            session_yr, lsr, _seq, employee, primary = line.strip().split("|")
            lsr = lsr.zfill(4)
            if session_yr == session and lsr in self.bills:
                sp_type = "primary" if primary == "1" else "cosponsor"
                try:
                    # Removes extra spaces in names
                    sponsor_name = self.legislators[employee]["name"].strip()
                    sponsor_name = " ".join(sponsor_name.split())
                    self.bills[lsr].add_sponsorship(
                        classification=sp_type,
                        name=sponsor_name,
                        entity_type="person",
                        primary=True if sp_type == "primary" else False,
                    )
                    self.bills[lsr].extras = {
                        "_code": self.legislators[employee]["seat"]
                    }
                except KeyError:
                    self.warning("Error, can't find person %s" % employee)

        # actions
        action_lines = (
            self.get(
                f"https://gc.nh.gov/dynamicdatadump/Docket.txt?x={self.cachebreaker}"
            )
            .content.decode("utf-8")
            .split("\n")
        )
        for line in action_lines:
            if len(line) < 1:
                continue
            # a few blank/irregular lines, irritating
            if "|" not in line:
                continue

            (session_yr, lsr, timestamp, bill_id, body, action, _) = line.split("|")

            if session_yr == session and lsr in self.bills:
                actor = "lower" if body == "H" else "upper"
                time = dt.datetime.strptime(timestamp, "%m/%d/%Y %H:%M:%S %p")
                action = action.strip()
                action_attr = self.categorizer.categorize(action)
                classification = action_attr["classification"]

                self.bills[lsr].add_action(
                    chamber=actor,
                    description=action,
                    date=time.strftime("%Y-%m-%d"),
                    classification=classification,
                )
                amendment_id = extract_amendment_id(action)
                if amendment_id:
                    self.bills[lsr].add_document_link(
                        note="amendment %s" % amendment_id,
                        url=AMENDMENT_URL % amendment_id,
                        on_duplicate="ignore",
                    )

        yield from self.scrape_votes(session)

        # save all bills
        for bill in self.bills:
            # bill.add_source(zip_url)
            self.add_source(self.bills[bill], bill, session)
            yield self.bills[bill]

    def add_source(self, bill, lsr, session):
        bill_url = (
            "https://gc.nh.gov/bill_status/legacy/bs2016/bill_docket.aspx?"
            + "lsr={}&sy={}&sortoption=&txtsessionyear={}".format(lsr, session, session)
        )
        bill.add_source(bill_url)

        bill_url = (
            "https://gc.nh.gov/bill_status/legacy/bs2016/bill_status.aspx?"
            + "lsr={}&sy={}&sortoption=&txtsessionyear={}".format(lsr, session, session)
        )
        bill.add_source(bill_url)

    def scrape_version_ids(self):

        for line in (
            self.get(
                "https://gc.nh.gov/dynamicdatadump/LsrsOnly.txt?x={}".format(
                    self.cachebreaker
                )
            )
            .content.decode("utf-8")
            .split("\n")
        ):
            if len(line) < 1:
                continue
            # a few blank/irregular lines, irritating
            if "|" not in line:
                continue

            line = line.split("|")
            file_id = line[2]
            lsr = line[0].split("-")
            lsr = lsr[1]
            self.versions_by_lsr[lsr] = file_id

    def scrape_amendments(self):
        for line in (
            self.get(
                "https://gc.nh.gov/dynamicdatadump/Docket.txt?x={}".format(
                    self.cachebreaker
                )
            )
            .content.decode("utf-8")
            .split("\n")
        ):
            if len(line) < 1:
                continue
            # a few blank/irregular lines, irritating
            if "|" not in line:
                continue

            line = line.split("|")
            lsr = line[1]

            amendment_regex = re.compile(r"Amendment # (\d{4}-\d+\w)", re.IGNORECASE)

            for match in amendment_regex.finditer(line[5]):
                self.amendments_by_lsr[lsr] = match.group(1)

    def scrape_votes(self, session):
        votes = {}
        other_counts = defaultdict(int)
        last_line = []
        vote_url = f"https://gc.nh.gov/dynamicdatadump/RollCallSummary.txt?x={self.cachebreaker}"
        lines = self.get(vote_url).content.decode("utf-8").splitlines()

        for line in lines:

            if len(line) < 2:
                continue

            if line.strip() == "":
                continue

            line = line.split("|")
            if len(line) < 14:
                if len(last_line + line[1:]) == 14:
                    line = last_line
                    self.warning("used bad vote line")
                else:
                    last_line = line
                    self.warning("bad vote line %s" % "|".join(line))
            session_yr = line[0].replace("\xef\xbb\xbf", "")
            body = line[1]
            vote_num = line[2]
            timestamp = line[3]
            bill_id = line[4].strip()
            yeas = int(line[5])
            nays = int(line[6])
            # present = int(line[7])
            # absent = int(line[8])
            motion = line[11].strip() or "[not available]"

            if session_yr == session and bill_id in self.bills_by_id:
                actor = "lower" if body == "H" else "upper"
                time = dt.datetime.strptime(timestamp, "%m/%d/%Y %I:%M:%S %p")
                time = pytz.timezone("America/New_York").localize(time).isoformat()
                # TODO: stop faking passed somehow
                passed = yeas > nays
                vote = Vote(
                    chamber=actor,
                    start_date=time,
                    motion_text=motion,
                    result="pass" if passed else "fail",
                    classification="passage",
                    bill=self.bills_by_id[bill_id],
                )
                vote.set_count("yes", yeas)
                vote.set_count("no", nays)
                vote.add_source(vote_url)
                vote.dedupe_key = session_yr + body + vote_num  # unique ID for vote
                votes[body + vote_num] = vote

        for line in (
            self.get(
                f"https://gc.nh.gov/dynamicdatadump/RollCallHistory.txt?x={self.cachebreaker}"
            )
            .content.decode("utf-8")
            .splitlines()
        ):
            if len(line) < 2:
                continue

            # 2016|H|2|330795||Yea|
            # 2012    | H   | 2    | 330795  | 964 |  HB309  | Yea | 1/4/2012 8:27:03 PM
            try:
                session_yr, body, v_num, _, employee, bill_id, vote, date = line.split(
                    "|"
                )
            except ValueError:
                # not enough keys in the split
                self.warning(f"Skipping {line}, didn't have all needed data for vote")
                continue
            if not bill_id:
                continue

            if session_yr == session and bill_id.strip() in self.bills_by_id:
                try:
                    leg = " ".join(self.legislators[employee]["name"].split())
                except KeyError:
                    self.warning(f"Error, can't find person {employee}")
                    continue

                vote = vote.strip()
                if body + v_num not in votes:
                    self.warning("Skipping processing this vote:")
                    self.warning("Bad ID: %s" % (body + v_num))
                    continue
                # code = self.legislators[employee]['seat']

                if vote == "Yea":
                    votes[body + v_num].yes(leg)
                elif vote == "Nay":
                    votes[body + v_num].no(leg)
                else:
                    votes[body + v_num].vote("other", leg)
                    # hack-ish, but will keep the vote count sync'd
                    other_counts[body + v_num] += 1
                    votes[body + v_num].set_count("other", other_counts[body + v_num])
        for vote in votes.values():
            yield vote

    def extract_until_number(self, text_string: str) -> str:
        """
        Extracts characters from a string until the first number is encountered.
        """
        match = re.match(r"^[^0-9]*", text_string)
        if match:
            return match.group(0)
        return ""
