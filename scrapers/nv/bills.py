import re
import pytz
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
import dateutil.parser
from openstates.scrape import Scraper, Bill, VoteEvent
from .common import session_slugs
from spatula import HtmlListPage, HtmlPage, CSS, XPath, SelectorError, SkipItem
from scrapelib import HTTPError

TZ = pytz.timezone("PST8PDT")
ACTION_CLASSIFIERS = (
    ("Approved by the Governor", ["executive-signature"]),
    ("Bill read. Veto not sustained", ["veto-override-passage"]),
    ("Bill read. Veto sustained", ["veto-override-failure"]),
    ("Enrolled and delivered to Governor", ["executive-receipt"]),
    ("From committee: .+? adopted", ["committee-passage"]),
    # the committee and chamber passage can be combined, see NV 80 SB 506
    (
        r"From committee: .+? pass(.*)Read Third time\.\s*Passed\.",
        ["committee-passage", "reading-3", "passage"],
    ),
    ("From committee: .+? pass", ["committee-passage"]),
    ("Prefiled. Referred", ["introduction", "referral-committee"]),
    ("Read first time. Referred", ["reading-1", "referral-committee"]),
    ("Read first time.", ["reading-1"]),
    ("Read second time.", ["reading-2"]),
    ("Read third time. Lost", ["failure", "reading-3"]),
    ("Read third time. Passed", ["passage", "reading-3"]),
    ("Read third time.", ["reading-3"]),
    ("Rereferred", ["referral-committee"]),
    ("Resolution read and adopted", ["passage"]),
    ("Enrolled and delivered", ["enrolled"]),
    ("To enrollment", ["passage"]),
    ("Approved by the Governor", ["executive-signature"]),
    ("Vetoed by the Governor", ["executive-veto"]),
)
VOTES_MAPPINGS = {
    "yea": "yes",
    "nay": "no",
    "excused": "excused",
    "not voting": "not voting",
    "absent": "absent",
}
# NV sometimes carries-over bills from previous sessions,
# without regard for bill number conflicts.
# so AB1* could get carried in, even if there's already an existing AB1
# The number of asterisks represent which past session it was pulled in from,
# which can include specials, and skip around, so this can't be automated.
# The list is at https://www.leg.state.nv.us/Session/81st2021/Reports/BillsListLegacy.cfm?DoctypeID=1
# where 81st2021 will need to be swapped in for the session code.
CARRYOVERS = {
    "80": {
        "*": "2017",
    },
    "81": {
        "*": "2019",
        "**": "2020Special32",
    },
    "82": {"*": "2021"},
    "83": {"*": "82", "**": "2023Special35"},
    "85": {"**": "2025Special36"},
}


def parse_date(date_str):
    return TZ.localize(dateutil.parser.parse(date_str))


def extract_bdr(title):
    """
    bills in NV start with a 'bill draft request'
    the number is in the title but it's useful as a structured extra
    """
    bdr = False
    bdr_regex = re.search(r"\(BDR\u00a0(\w+-\w+)\)", title)
    if bdr_regex:
        bdr = bdr_regex.group(1)
    return bdr


def shorten_bill_title(title):
    """
    Used in cases where the bill title exceeds the
    300-character limit that we have on this attribute.
    """
    title_bdr_re = re.compile(r"(.+)(\(BDR \w+-\w+\))")
    title_bdr_match = title_bdr_re.search(title)
    bdr_full = ""
    if title_bdr_match:
        title, bdr_full = title_bdr_match.groups()
    title = f"{title[:280]}... + {bdr_full}"
    return title


class BillTitleLengthError(BaseException):
    def __init__(self, bill_id, title):
        super().__init__(
            f"Title of {bill_id} exceeds 300 characters:"
            f"\n title -> '{title}'"
            f"\n character length -> {len(title)}"
        )


@dataclass
class BillStub:
    source_url: str
    identifier: str
    session: str
    subjects: list


class SubjectMapping(HtmlPage):
    example_input = {"session": "81"}

    def get_source_from_input(self):
        session = self.input["session"]
        slug = session_slugs[session]
        if "Special" in session:
            year = slug[4:8]
            url = f"https://www.leg.state.nv.us/App/NELIS/REL/{slug}/Bills/List"
        elif (len(session) >= 4 and int(session[0:4]) <= 2024) or (
            len(session) < 4 and int(session) < 83
        ):
            # Use the old format of URL for sessions < 2025
            year = slug[4:]
            url = (
                f"https://www.leg.state.nv.us/Session/{slug}/Reports/"
                f"TablesAndIndex/{year}_{session}-index.html"
            )
        else:
            # Use new format URL for more recent sessions
            url = f"https://www.leg.state.nv.us/App/NELIS/REL/{slug}/Bills/List"
        return url

    def process_page(self):
        subjects = defaultdict(set)

        # first, a bit about this page:
        # Level0 are the bolded titles
        # Level1,2,3,4 are detailed titles, contain links to bills
        # all links under a Level0 we can consider categorized by it
        # there are random newlines *everywhere* that should get replaced

        subject = None

        for p in self.root.xpath("//p"):
            if p.get("class") == "Level0":
                subject = p.text_content().replace("\r\n", " ")
            else:
                if subject:
                    for a in p.xpath(".//a"):
                        bill_id = a.text.replace("\r\n", "") if a.text else None
                        subjects[bill_id].add(subject)
        return subjects


class BillList(HtmlListPage):
    example_input = {"session": "81"}
    selector = CSS(".row a")
    dependencies = {"subject_mapping": SubjectMapping}

    def get_source_from_input(self):
        slug = session_slugs[self.input["session"]]
        # PageSize 2**31 from their site
        return (
            f"https://www.leg.state.nv.us/App/NELIS/REL/{slug}/"
            "HomeBill/BillsTab?selectedTab=List&Filters.PageSize=2147483647"
            f"&_={time.time()}"
        )

    def process_item(self, item):
        link = item.get("href")
        identifier = item.text

        if link is None:
            return

        self.logger.info(f"About to process BillTabDetail for {identifier} at {link}")
        return BillTabDetail(
            BillStub(
                link,
                identifier,
                self.input["session"],
                list(self.subject_mapping[identifier]),
            )
        )


class BillTabDetail(HtmlPage):
    example_input = BillStub(
        "https://www.leg.state.nv.us/App/NELIS/REL/81st2021/Bill/7262/Overview",
        "AB20",
        "81",
        ["test subject"],
    )

    def get_source_from_input(self):
        bill_key = self.input.source_url.split("/")[-2]
        slug = session_slugs[self.input.session]
        url = (
            f"https://www.leg.state.nv.us/App/NELIS/REL/{slug}/Bill/"
            f"FillSelectedBillTab?selectedTab=Overview&billKey={bill_key}"
            f"&_={time.time()}"
        )
        return url

    def process_error_response(self, exception: Exception) -> None:
        message = f"Encountered error fetching Bill Overview for {self.input.identifier}, skipping {self.input.source_url}"
        self.logger.warning(message)
        raise SkipItem(message)

    def get_column_div(self, name):
        # lots of places where we have a <div class='col-md-2 font-weight-bold'>
        # followeed by a <div class='col'>
        # with interesting content in the latter element
        return XPath(
            f"//div[contains(text(),'{name}')]/following-sibling::div[@class='col']"
        ).match_one(self.root)

    def add_sponsors(self, bill, sponsor_links, primary):
        seen = set()
        for link in sponsor_links:
            name = link.text_content().strip()
            if "Sponsors" in name or name == "":
                continue
            # Removes leg position from name
            # Use position to determine chamber
            # Example: Assemblywoman Alexis Hansen
            # Also check if sponsor is an organization or person
            # Example: "Assembly Committee on Government Affairs" is an organization
            chamber = None
            entity_type = "person"
            if "committee" in name.lower():
                entity_type = "organization"
            if name.split()[0] in [
                "Assemblywoman",
                "Assemblyman",
                "Assemblymember",
                "Senator",
            ]:
                chamber = "lower" if "Assembly" in name.split()[0] else "upper"
                name = " ".join(name.split()[1:]).strip()
            if name not in seen:
                seen.add(name)
                bill.add_sponsorship(
                    name=name,
                    classification="sponsor" if primary else "cosponsor",
                    entity_type=entity_type,
                    primary=primary,
                    chamber=chamber,
                )

    def add_actions(self, bill, chamber):
        # first action is from originating chamber
        actor = chamber

        # Sometimes NV bill page might just not have an actions section at all
        try:
            for row in XPath("//caption/parent::table/tbody/tr").match(self.root):
                date, action, _ = [x.text for x in row.getchildren()]
                date = parse_date(date)

                # catch chamber changes
                if action.startswith("In Assembly"):
                    actor = "lower"
                elif action.startswith("In Senate"):
                    actor = "upper"
                elif "Governor" in action:
                    actor = "executive"

                action_type = []
                for pattern, atype in ACTION_CLASSIFIERS:
                    if not re.search(pattern, action, re.IGNORECASE):
                        continue
                    # sometimes NV returns multiple actions in the same posting
                    # so don't break here
                    action_type = action_type + atype

                if not action_type:
                    action_type = None
                else:
                    action_type = list(set(action_type))

                related_entities = []
                if "Committee on" in action:
                    committees = re.findall(r"Committee on ([a-zA-Z, ]*)\.", action)
                    for committee in committees:
                        related_entities.append(
                            {"type": "committee", "name": committee}
                        )

                bill.add_action(
                    description=action,
                    date=date,
                    chamber=actor,
                    classification=action_type,
                    related_entities=related_entities,
                )
        except SelectorError:
            pass

    def process_page(self):
        chamber = "upper" if self.input.identifier.startswith("S") else "lower"
        short_title = self.get_column_div("Summary").text
        long_title = CSS("#title").match_one(self.root).text

        if "*" in self.input.identifier:
            stars = re.search(r"\*+", self.input.identifier).group()
            if (
                self.input.session in CARRYOVERS
                and stars in CARRYOVERS[self.input.session]
            ):
                self.input.identifier = re.sub(
                    r"\*+",
                    "-" + CARRYOVERS[self.input.session][stars],
                    self.input.identifier,
                )
            else:
                self.logger.error(
                    f"Unidentified carryover bill {self.input.identifier}. Update CARRYOVERS dict in bills.py"
                )
                return

        if len(short_title) > 300:
            self.logger.warning(
                f"Short title too long, truncating. {self.input.identifier}"
            )
            short_title = shorten_bill_title(short_title)

        bill = Bill(
            identifier=self.input.identifier,
            legislative_session=self.input.session,
            title=short_title,
            chamber=chamber,
        )
        bill.subject = self.input.subjects
        # use the pretty source URL
        bill.add_source(self.input.source_url)
        bill.add_title(long_title)

        try:
            sponsors = self.get_column_div("Primary Sponsor")
            self.add_sponsors(bill, CSS("a").match(sponsors), primary=True)
        except SelectorError:
            pass
        try:
            cosponsors = self.get_column_div("Co-Sponsor")
            self.add_sponsors(bill, CSS("a").match(cosponsors), primary=False)
        except SelectorError:
            pass
        # TODO: figure out cosponsor div name, can't find any as of Feb 2021
        self.add_actions(bill, chamber)

        bdr = extract_bdr(short_title)
        if bdr:
            bill.extras["BDR"] = bdr

        text_url = self.source.url.replace("Overview", "Text")
        yield BillTabText(bill, source=text_url)

        # TODO: figure out vote events VotesTab -> VoteList -> VoteMembers
        votes_url = self.source.url.replace("Overview", "Votes")
        yield VotesTab(bill, source=votes_url)


class BillTabText(HtmlPage):
    example_source = (
        "https://www.leg.state.nv.us/App/NELIS/REL/82nd2023/Bill/"
        "GetBillVoteMembers?voteKey=10429&voteResultPanel=All"
    )

    def process_page(self):
        bill = self.input
        # some BDRs have no text link
        for row in CSS(".d-md-none a").match(self.root, min_items=0):
            title = row.text_content()
            link = row.get("href")
            bill.add_version_link(
                title, link, media_type="application/pdf", on_duplicate="ignore"
            )
        ex_url = self.source.url.replace("Text", "Exhibits")

        try:
            return ExhibitTabText(bill, source=ex_url)
        except HTTPError:
            self.warning(f"Failure on exhibit url {ex_url}")
            am_url = self.source.url.replace("Text", "Amendments")
            return AmendmentTabText(bill, source=am_url)


class ExhibitTabText(HtmlPage):
    example_source = (
        "https://www.leg.state.nv.us/App/NELIS/REL/82nd2023/Bill/"
        "FillSelectedBillTab?selectedTab=Exhibits&billKey=9581"
    )

    def process_error_response(self, exception: Exception) -> None:
        message = f"Encountered error fetching Exhibits tab, skipping {self.source}"
        self.logger.warning(message)
        raise SkipItem(message)

    def process_page(self):
        bill = self.input
        for row in CSS("li.my-4 a").match(self.root, min_items=0):
            title = row.text_content()
            link = row.get("href")
            bill.add_document_link(
                title, link, media_type="application/pdf", on_duplicate="ignore"
            )
        am_url = self.source.url.replace("Text", "Amendments")
        return AmendmentTabText(bill, source=am_url)


class AmendmentTabText(HtmlPage):
    example_source = (
        "https://www.leg.state.nv.us/App/NELIS/REL/82nd2023/Bill/"
        "FillSelectedBillTab?selectedTab=Amendments&billKey=10039"
    )

    def process_page(self):
        bill = self.input
        for row in CSS("col-11 col-md").match(self.root, min_items=0):
            title = row.text_content()
            link = row.get("href")
            bill.add_version_link(
                title, link, media_type="application/pdf", on_duplicate="ignore"
            )

        fn_url = self.source.url.replace("Text", "FiscalNotes")
        return FiscalTabText(bill, source=fn_url)


class FiscalTabText(HtmlPage):
    example_source = (
        "https://www.leg.state.nv.us/App/NELIS/REL/82nd2023/Bill/"
        "FillSelectedBillTab?selectedTab=FiscalNotes&billKey=9528"
    )

    def process_page(self):
        bill = self.input
        for row in CSS("ul.list-unstyled li a").match(self.root, min_items=0):
            title = row.text_content()
            title = f"Fiscal Note: {title}"
            link = row.get("href")
            bill.add_document_link(
                title, link, media_type="application/pdf", on_duplicate="ignore"
            )
        return bill


class VotesTab(HtmlPage):
    example_source = (
        "https://www.leg.state.nv.us/App/NELIS/REL/82nd2023/Bill/"
        "FillSelectedBillTab?selectedTab=Votes&billKey=9545"
    )

    def process_page(self):
        bill = self.input

        votes = CSS("#vote-revisions a", min_items=0).match(self.root)
        if len(votes) > 0:
            votes_url = votes[0].get("href")
            return VoteList(dict(bill=bill, url=self.source.url), source=votes_url)


class VoteList(HtmlPage):
    example_source = (
        "https://www.leg.state.nv.us/App/NELIS/REL/82nd2023/Bill/"
        "GetBillVotes?billKey=9545&voteTypeId=3"
    )

    def process_page(self):
        input_data = self.input
        vote_url = input_data["url"]
        bill = input_data["bill"]

        summaries = CSS("h2.h3", min_items=0).match(self.root)
        if len(summaries) == 0:
            return
        summaries = [summary.text for summary in summaries]

        vote_re = re.compile(
            r"(?P<vt_option>Yea|Nay|Excused|Absent|Not Voting): (?P<vt_cnt>\d+)",
            re.U | re.I,
        )
        date_re = re.compile(r"Date\s+(?P<date>.*)", re.U | re.I)
        index = 0

        date_motion_counts = {}
        for row in CSS(".vote-revision", min_items=0).match(self.root):
            summary = summaries[index]
            index += 1
            chamber = (
                "lower"
                if "Assembly" in summary
                else ("upper" if "Senate" in summary else "")
            )

            vote_options = {}
            start_date = None

            for child_row in CSS("ul li", min_items=0).match(row):
                content = child_row.text_content().strip()

                vote_match = re.match(vote_re, content)
                if vote_match:
                    vo = vote_match.groupdict()
                    vote_options[vo["vt_option"].lower()] = int(vo["vt_cnt"])

                date_match = re.match(date_re, content)
                if date_match:
                    start_date = date_match.groupdict()["date"]
                    start_date = parse_date(start_date)

            # sometimes two votes with the same motion happen on the same day
            # hence we need to make motion text unique otherwise import fails
            date_motion = f"{start_date.date()}{summary}"
            if start_date is not None and date_motion in date_motion_counts:
                num_existing = date_motion_counts[date_motion]
                summary = f"{summary} ({num_existing + 1})"
                date_motion_counts[date_motion] += 1
            else:
                date_motion_counts[date_motion] = 1

            vote = VoteEvent(
                chamber=chamber,
                motion_text=summary,
                result="pass" if vote_options["yea"] > vote_options["nay"] else "fail",
                classification="passage",
                start_date=start_date,
                bill=bill,
            )
            vote.add_source(vote_url)
            for name, value in vote_options.items():
                vote.set_count(VOTES_MAPPINGS.get(name, "other"), value)

            votes_members_url = CSS(".panelAllVoters a").match_one(row).get("href")
            yield VoteMembers(vote, source=votes_members_url)


class VoteMembers(HtmlPage):
    example_source = (
        "https://www.leg.state.nv.us/App/NELIS/REL/82nd2023/Bill/"
        "GetBillVotes?billKey=9545&voteTypeId=3"
    )

    def process_page(self):
        vote = self.input
        member_re = re.compile(
            r"\s+(?P<member>.*)\s+\((?P<vote_type>.*)\)\s+", re.U | re.I
        )

        for row in CSS(".vote").match(self.root):
            content = row.text_content()
            match = member_re.match(content)
            if match:
                v = match.groupdict()
                voter = v["member"].strip()
                vote_type = VOTES_MAPPINGS.get(v["vote_type"].lower().strip(), "other")
                vote.vote(vote_type, voter)

        yield vote


class NVBillScraper(Scraper):
    def scrape(self, session=None):
        logging.getLogger("scrapelib").setLevel(logging.WARNING)
        bill_list = BillList({"session": session})
        yield from bill_list.do_scrape()
