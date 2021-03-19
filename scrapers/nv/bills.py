import re
import pytz
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
import dateutil.parser
from openstates.scrape import Scraper, Bill
from .common import session_slugs
from spatula import HtmlListPage, HtmlPage, CSS, XPath, page_to_items, SelectorError


TZ = pytz.timezone("PST8PDT")
ACTION_CLASSIFIERS = (
    ("Approved by the Governor", "executive-signature"),
    ("Bill read. Veto not sustained", "veto-override-passage"),
    ("Bill read. Veto sustained", "veto-override-failure"),
    ("Enrolled and delivered to Governor", "executive-receipt"),
    ("From committee: .+? adopted", "committee-passage"),
    ("From committee: .+? pass", "committee-passage"),
    ("Prefiled. Referred", ["introduction", "referral-committee"]),
    ("Read first time. Referred", ["reading-1", "referral-committee"]),
    ("Read first time.", "reading-1"),
    ("Read second time.", "reading-2"),
    ("Read third time. Lost", ["failure", "reading-3"]),
    ("Read third time. Passed", ["passage", "reading-3"]),
    ("Read third time.", "reading-3"),
    ("Rereferred", "referral-committee"),
    ("Resolution read and adopted", "passage"),
    ("Vetoed by the Governor", "executive-veto"),
)

# NV sometimes carries-over bills from previous sessions,
# without regard for bill number conflicts. 
# so AB1* could get carried in, even if there's already an existing AB1
# The number of asterisks represent which past session it was pulled in from,
# which can include specials, and skip around, so this can't be automated.
# The list is at https://www.leg.state.nv.us/Session/81st2021/Reports/BillsListLegacy.cfm?DoctypeID=1
# where 81st2021 will need to be swapped in for the session code.
CARRYOVERS = {
    '80': {
        '*': '2017',
    },
    '81': {
        '*': '2019',
        '**': '2020Special32',
    }
}

def parse_date(date_str):
    return TZ.localize(dateutil.parser.parse(date_str))


def extract_bdr(title):
    """
    bills in NV start with a 'bill draft request'
    the number is in the title but it's useful as a structured extra
    """
    bdr = False
    bdr_regex = re.search(r"\(BDR (\w+\-\w+)\)", title)
    if bdr_regex:
        bdr = bdr_regex.group(1)
    return bdr


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
        year = slug[4:]
        url = (
            f"https://www.leg.state.nv.us/Session/{slug}/Reports/"
            f"TablesAndIndex/{year}_{session}-index.html"
        )
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
            if "Sponsors" in name:
                continue
            # Removes leg position from name
            # Example: Assemblywoman Alexis Hansen
            if name.split()[0] in ["Assemblywoman", "Assemblyman", "Senator"]:
                name = " ".join(name.split()[1:]).strip()
            if name not in seen:
                seen.add(name)
                bill.add_sponsorship(
                    name=name,
                    classification="sponsor" if primary else "cosponsor",
                    entity_type="person",
                    primary=primary,
                )

    def add_actions(self, bill, chamber):
        # first action is from originating chamber
        actor = chamber

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

            action_type = None
            for pattern, atype in ACTION_CLASSIFIERS:
                if re.match(pattern, action):
                    action_type = atype
                    break

            related_entities = []
            if "Committee on" in action:
                committees = re.findall(r"Committee on ([a-zA-Z, ]*)\.", action)
                for committee in committees:
                    related_entities.append({"type": "committee", "name": committee})

            bill.add_action(
                description=action,
                date=date,
                chamber=actor,
                classification=action_type,
                related_entities=related_entities,
            )

    def process_page(self):
        chamber = "upper" if self.input.identifier.startswith("S") else "lower"
        short_title = self.get_column_div("Summary").text
        long_title = CSS("#title").match_one(self.root).text

        if '*' in self.input.identifier:
            stars = re.search(r'\*+', self.input.identifier).group()
            if self.input.session in CARRYOVERS and stars in CARRYOVERS[self.input.session]:
                self.input.identifier = re.sub(r'\*+', '-'+CARRYOVERS[self.input.session][stars], self.input.identifier)
            else:
                self.logger.error(f"Unidentified carryover bill {self.input.identifier}. Update CARRYOVERS dict in bills.py")
                return


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


class BillTabText(HtmlPage):
    example_source = (
        "https://www.leg.state.nv.us/App/NELIS/REL/81st2021/Bill/"
        "FillSelectedBillTab?selectedTab=Text&billKey=7366"
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
        return bill


class NVBillScraper(Scraper):
    def scrape(self, session=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)
        logging.getLogger("scrapelib").setLevel(logging.WARNING)
        bill_list = BillList({"session": session})
        yield from page_to_items(self, bill_list)
