# -*- coding: utf-8 -*-
import re
import os
import datetime
import pytz
import scrapelib
import lxml.html
from openstates.scrape import Scraper, Bill, VoteEvent
from openstates.utils import convert_pdf

central = pytz.timezone("US/Central")

# from ._utils import canonicalize_url


session_details = {
    "102nd": {
        "speaker": "Welch",
        "president": "Harmon",
        "params": {"GA": "102", "SessionId": "110"},
    },
    "101st": {
        "speaker": "Madigan",
        "president": "Cullerton",
        "params": {"GA": "101", "SessionId": "108"},
    },
    "100th-special": {
        "speaker": "Madigan",
        "president": "Cullerton",
        "params": {"GA": "100", "SessionID": "92", "SpecSess": "1"},
    },
    "100th": {
        "speaker": "Madigan",
        "president": "Cullerton",
        "params": {"GA": "100", "SessionId": "91"},
    },
    "99th": {
        "speaker": "Madigan",
        "president": "Cullerton",
        "params": {"GA": "99", "SessionId": "88"},
    },
    "98th": {
        "speaker": "Madigan",
        "president": "Cullerton",
        "params": {"GA": "98", "SessionId": "85"},
    },
    "97th": {
        "params": {"GA": "97", "SessionId": "84"},
        "speaker": "Madigan",
        "president": "Cullerton",
    },
    "96th": {
        "params": {"GA": "96", "SessionId": "76"},
        "speaker": "Madigan",
        "president": "Cullerton",
    },
    "96th-special": {
        "params": {"GA": "96", "SessionId": "82", "SpecSess": "1"},
        "speaker": "Madigan",
        "president": "Cullerton",
    },
    "95th": {
        "params": {"GA": "95", "SessionId": "51"},
        "speaker": "Madigan",
        "president": "Jones, E.",
    },
    "95th-special": {
        "params": {"GA": "95", "SessionId": "52", "SpecSess": "1"},
        "speaker": "Madigan",
        "president": "Jones, E.",
    },
    "94th": {
        "params": {"GA": "94", "SessionId": "50"},
        "speaker": "Madigan",
        "president": "Jones, E.",
    },
    "93rd": {
        "params": {"GA": "93", "SessionId": "3"},
        "speaker": "Madigan",
        "president": "Jones, E.",
    },
    "93rd-special": {
        "params": {"GA": "93", "SessionID": "14", "SpecSess": "1"},
        "speaker": "Madigan",
        "president": "Jones, E.",
    },
}


SPONSOR_REFINE_PATTERN = re.compile(
    r"^Added (?P<spontype>.+) (?P<title>Rep|Sen)\. (?P<name>.+)"
)
SPONSOR_TYPE_REFINEMENTS = {
    "Chief Co-Sponsor": "cosponsor",
    "as Chief Co-Sponsor": "cosponsor",
    "Alternate Chief Co-Sponsor": "cosponsor",
    "as Alternate Chief Co-Sponsor": "cosponsor",
    "as Co-Sponsor": "cosponsor",
    "Alternate Co-Sponsor": "cosponsor",
    "as Alternate Co-Sponsor": "cosponsor",
    "Co-Sponsor": "cosponsor",
}


VERSION_TYPES = ("Introduced", "Engrossed", "Enrolled", "Re-Enrolled")
FULLTEXT_DOCUMENT_TYPES = ("Public Act", "Governor's Message")
# not as common, but maybe should just be added to FULLTEXT_DOCUMENT_TYPES?
# Amendatory Veto Motion \d{3}
# Conference Committee Report \d{3}

DOC_TYPES = {
    "B": "bill",
    "R": "resolution",
    "JR": "joint resolution",
    "JRCA": "constitutional amendment",
}

# see http://openstates.org/categorization/
_action_classifiers = (
    (re.compile(r"Amendment No. \d+ Filed"), ["amendment-introduction"]),
    (re.compile(r"Amendment No. \d+ Tabled"), ["amendment-failure"]),
    (re.compile(r"Amendment No. \d+ Adopted"), ["amendment-passage"]),
    (re.compile(r"(Pref|F)iled with"), ["filing"]),
    (re.compile(r"Arrived? in"), ["introduction"]),
    (re.compile(r"First Reading"), ["reading-1"]),
    (re.compile(r"(Recalled to )?Second Reading"), ["reading-2"]),
    (re.compile(r"(Re-r|R)eferred to"), ["referral-committee"]),
    (re.compile(r"(Re-a|A)ssigned to"), ["referral-committee"]),
    (re.compile(r"Sent to the Governor"), ["executive-receipt"]),
    (re.compile(r"Governor Approved"), ["executive-signature"]),
    (re.compile(r"Governor Vetoed"), ["executive-veto"]),
    (re.compile(r"Governor Item"), ["executive-veto-line-item"]),
    (re.compile(r"Both Houses Override Total Veto"), ["veto-override-passage"]),
    (re.compile(r"Governor Amendatory Veto"), ["executive-veto"]),
    (re.compile(r"Public Act"), ["became-law"]),
    (
        re.compile(
            r"^(?:Recommends )?Do Pass(?: as Amended)?(?: / Short Debate)?(?: / Standard Debate)?"
        ),
        ["committee-passage"],
    ),
    (re.compile(r"Amendment.+Concur"), []),
    (re.compile(r"Motion Do Pass(?: as Amended)?(?: - Lost)?"), ["committee-failure"]),
    (re.compile(r"Motion Do Pass(?: as Amended)?"), ["committee-passage"]),
    (re.compile(r".*Be Adopted(?: as Amended)?"), ["committee-passage-favorable"]),
    (re.compile(r"Third Reading .+? Passed"), ["reading-3", "passage"]),
    (re.compile(r"Third Reading .+? Lost"), ["reading-3", "failure"]),
    (re.compile(r"Third Reading"), ["reading-3"]),
    (re.compile(r"Resolution Adopted"), ["passage"]),
    (re.compile(r"Resolution Lost"), ["failure"]),
    (re.compile(r"Session Sine Die"), ["failure"]),
    (re.compile(r"Tabled"), ["withdrawal"]),
    (re.compile(r"Motion To Adopt"), ["passage"]),
)

_OTHER_FREQUENT_ACTION_PATTERNS_WHICH_ARE_CURRENTLY_UNCLASSIFIED = [
    r"Accept Amendatory Veto - (House|Senate) (Passed|Lost) \d+-\d+\d+.?",
    r"Amendatory Veto Motion - (.+)",
    r"Balanced Budget Note (.+)",
    r"Effective Date(\s+.+ \d{4})?(;.+)?",
    r"To .*Subcommittee",
    r"Note Requested",
    r"Note Filed",
    r"^Public Act",
    r"Appeal Ruling of Chair",
    r"Added .*Sponsor",
    r"Remove(d)? .*Sponsor",
    r"Sponsor Removed",
    r"Sponsor Changed",
    r"^Chief .*Sponsor",
    r"^Co-Sponsor",
    r"Deadline Extended.+9\(b\)",
    r"Amendment.+Approved for Consideration",
    r"Approved for Consideration",
    r"Amendment.+Do Adopt",
    r"Amendment.+Concurs",
    r"Amendment.+Lost",
    r"Amendment.+Withdrawn",
    r"Amendment.+Motion.+Concur",
    r"Amendment.+Motion.+Table",
    r"Amendment.+Rules Refers",
    r"Amendment.+Motion to Concur Recommends be Adopted",
    r"Amendment.+Assignments Refers",
    r"Amendment.+Assignments Refers",
    r"Amendment.+Held",
    r"Motion.+Suspend Rule 25",
    r"Motion.+Reconsider Vote",
    r"Placed on Calendar",
    r"Amendment.+Postponed - (?P<committee>.+)",
    r"Postponed - (?P<committee>.+)",
    r"Secretary's Desk",
    r"Rule 2-10 Committee Deadline Established",
    r"^Held in (?P<committee>.+)",
]

_archived_action_classifiers = {
    "GOVERNOR AMENDATORY VETO": "executive-veto",
    "GOVERNOR APPROVED": "executive-signature",
    "SENT TO THE GOVERNOR": "executive-receipt",
    "REFERRED ": "referral-committee",
    "FIRST READING": "reading-1",
    "SECOND READING": "reading-2",
    "THIRD READING": ["reading-3"],
    "THIRD READING - PASSED": ["passage", "reading-3"],
    "THIRD READING/SHORT DEBATE/PASSED": ["passage", "reading-3"],
    "FILED": "introduction",
    "ADOPTED": "passage",
    "ASSIGNED TO COMMITTEE": "referral-committee",
}


VOTE_VALUES = ["NV", "Y", "N", "E", "A", "P", "-"]

COMMITTEE_CORRECTIONS = {
    "Elementary & Secondary Education: School Curriculum & Policies": "Elem Sec Ed: School Curric Policies",
    "Elementary & Secondary Education: Licensing, Administration & Oversight": "Elem Sec Ed: Licensing, Admin.",
    "Elementary & Secondary Education:  Charter School Policy": "Elem Sec Ed:  Charter School Policy",
    "Transportation: Regulation, Roads & Bridges": "Transportation: Regulation, Roads",
    "Business Incentives for Local Communities": "Business Incentives for Local Comm.",
    "Museums, Arts, & Cultural Enhancement": "Museums, Arts, & Cultural Enhanceme",
    "Health Care Availability & Accessibility": "Health Care Availability & Access",
    "Construction Industry & Code Enforcement": "Construction Industry & Code Enforc",
    "Appropriations-Elementary & Secondary Education": "Approp-Elementary & Secondary Educ",
    "Tourism, Hospitality & Craft Industries": "Tourism, Hospitality & Craft Ind.",
    "Government Consolidation &  Modernization": "Government Consolidation &  Modern",
    "Community College Access & Affordability": "Community College Access & Afford.",
}

DUPE_VOTES = {
    "https://ilga.gov/legislation/votehistory/100/house/committeevotes/"
    "10000HB2457_16401.pdf"
}


def group(lst, n):
    # from http://code.activestate.com/recipes/303060-group-a-list-into-sequential-n-tuples/
    for i in range(0, len(lst), n):
        val = lst[i : i + n]
        if len(val) == n:
            yield tuple(val)


def _categorize_action(action):
    related_orgs = []

    for pattern, atype in _action_classifiers:

        if pattern.findall(action):
            if "referral-committee" in atype:
                related_orgs = [pattern.sub("", action).strip()]
            for each in atype:
                if each.startswith("committee"):
                    org = pattern.sub("", action).split(";")[0].strip()
                    org = re.sub(" *Committee *$", "", org)
                    if org in COMMITTEE_CORRECTIONS:
                        org = COMMITTEE_CORRECTIONS[org]
                    related_orgs = [org]
            return atype, related_orgs

    return None, related_orgs


def chamber_slug(chamber):
    if chamber == "lower":
        return "H"
    return "S"


class IlBillScraper(Scraper):
    LEGISLATION_URL = "https://ilga.gov/legislation/grplist.asp"
    localize = pytz.timezone("America/Chicago").localize

    def get_bill_urls(self, chamber, session, doc_type):
        params = session_details[session]["params"]
        params["num1"] = "1"
        params["num2"] = "10000"
        params["DocTypeID"] = doc_type
        html = self.get(self.LEGISLATION_URL, params=params).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(self.LEGISLATION_URL)

        for bill_url in doc.xpath("//li/a/@href"):
            yield bill_url

    def scrape(self, session=None):
        session_id = session
        # scrape a single bill for debug
        # yield from self.scrape_bill(
        #     'lower', '101st', 'HB', 'https://ilga.gov/legislation/BillStatus.asp?DocNum=
        # 2488&GAID=15&DocTypeID=HB&LegId=118516&SessionID=108&GA=101'
        # )

        # Sessions that run from 1997 - 2002. Last few sessiosn before bills were PDFs
        if session in ["90th", "91st", "92nd"]:
            yield from self.scrape_archive_bills(session)
        else:
            for chamber in ("lower", "upper"):
                for doc_type in [
                    chamber_slug(chamber) + doc_type for doc_type in DOC_TYPES
                ]:
                    for bill_url in self.get_bill_urls(chamber, session_id, doc_type):
                        yield from self.scrape_bill(
                            chamber, session_id, doc_type, bill_url
                        )

            # special non-chamber cases
            for bill_url in self.get_bill_urls(chamber, session_id, "AM"):
                yield from self.scrape_bill(
                    chamber, session_id, "AM", bill_url, "appointment"
                )

            # TODO: get joint session resolution added to python-opencivicdata
            # for bill_url in self.get_bill_urls(chamber, session_id, 'JSR'):
            #     bill, votes = self.scrape_bill(chamber, session_id, 'JSR', bill_url,
            #                                    'joint session resolution')
            #     yield bill
            #     yield from votes

    def scrape_archive_bills(self, session):
        session_abr = session[0:2]
        url = f"https://www.ilga.gov/legislation/legisnet{session_abr}/{session_abr}gatoc.html"
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        bill_numbers_sections = doc.xpath("//table//a/@href")

        # Contains multiple bills
        for bill_numbers_section_url in bill_numbers_sections:
            bill_section_html = self.get(bill_numbers_section_url).text
            bill_section_doc = lxml.html.fromstring(bill_section_html)
            bill_section_doc.make_links_absolute(bill_numbers_section_url)

            if "/sb" in bill_numbers_section_url or "/sr" in bill_numbers_section_url:
                chamber = "upper"
            else:
                chamber = "lower"

            bills_urls = bill_section_doc.xpath("//blockquote/a/@href")

            # Actual Bill Pages
            for bill_url in bills_urls:

                bill_html = self.get(bill_url).text
                bill_doc = lxml.html.fromstring(bill_html)
                bill_doc.make_links_absolute(bill_url)

                sponsors = bill_doc.xpath('//pre/a[contains(@href, "sponsor")]')

                bill_id = bill_doc.xpath('//font[contains (., "Status of")]')
                if len(bill_id) < 1:
                    bill_id = bill_doc.xpath('//font[contains (., "Summary of")]')
                bill_id = bill_id[0].text_content().split()[-1]

                if "JRCA" in bill_id:
                    classification = "constitutional amendment"
                elif "JR" in bill_id:
                    classification = "joint resolution"
                elif "R" in bill_id:
                    classification = "resolution"
                else:
                    classification = "bill"

                if "status" in bill_url:
                    # Currently on status page, but need info for summary page
                    summary_page_url = bill_doc.xpath(
                        '//a[contains (., "Bill Summary")]/@href'
                    )[0]
                    summary_page_html = self.get(summary_page_url).text
                    summary_page_doc = lxml.html.fromstring(summary_page_html)
                    summary_page_doc.make_links_absolute(summary_page_url)
                else:
                    # Currently on summary page, but need info for status page
                    summary_page_doc = bill_doc
                    summary_page_url = bill_url
                    bill_url = bill_doc.xpath('//a[contains (., "Bill Status")]/@href')[
                        0
                    ]
                    bill_html = self.get(bill_url).text
                    bill_doc = lxml.html.fromstring(bill_html)
                    bill_doc.make_links_absolute(bill_url)

                summary_text = (
                    summary_page_doc.xpath("//pre")[0].text_content().splitlines()
                )
                for x in range(len(summary_text)):
                    line = summary_text[x]
                    if "Short description:" in line:
                        bill_title = summary_text[x + 1]

                bill = Bill(
                    bill_id,
                    legislative_session=session,
                    title=bill_title,
                    chamber=chamber,
                    classification=classification,
                )
                bill.add_source(summary_page_url)
                bill.add_source(url)

                # Sponsors
                for sponsor in sponsors:
                    if sponsor.text_content():
                        bill.add_sponsorship(
                            name=sponsor.text_content(),
                            classification="cosponsor",
                            entity_type="person",
                            primary=False,
                        )

                # Bill version
                version_url = bill_doc.xpath('//a[contains (., "Full Text")]/@href')[0]
                bill.add_version_link(bill_id, version_url, media_type="text/html")

                # Actions
                bill_text = bill_doc.xpath("//pre")
                if bill_text:
                    bill_text = bill_text[0].text_content().splitlines()
                    for x in range(len(bill_text)):
                        line = bill_text[x].split()
                        # Regex is looking for this format: JAN-11-2001 or 99-02-17
                        if line and (
                            re.match(r"\D\D\D-\d\d-\d\d\d\d", line[0])
                            or re.match(r"\d\d-\d\d-\d\d", line[0])
                        ):
                            if session in ["91st", "90th"]:
                                action_date = datetime.datetime.strptime(
                                    line[0], "%y-%m-%d"
                                )
                            else:
                                action_date = datetime.datetime.strptime(
                                    line[0], "%b-%d-%Y"
                                )

                            action_date = central.localize(action_date)
                            action_date = action_date.isoformat()

                            action = " ".join(line[2:])
                            if line[1] == "S":
                                action_chamber = "upper"
                            else:
                                action_chamber = "lower"

                            for pattern, atype in _archived_action_classifiers.items():
                                if action.startswith(pattern):
                                    break
                            else:
                                atype = None
                            bill.add_action(
                                action,
                                action_date,
                                chamber=action_chamber,
                                classification=atype,
                            )

                yield bill

    def scrape_bill(self, chamber, session, doc_type, url, bill_type=None):
        try:
            html = self.get(url).text
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(url)
        except scrapelib.HTTPError as e:
            assert (
                "500" in e.args[0]
            ), "Unexpected error when accessing page: {}".format(e)
            self.warning("500 error for bill page; skipping bill")
            return

        # bill id, title, summary
        bill_num = re.findall(r"DocNum=(\d+)", url)[0]
        bill_type = bill_type or DOC_TYPES[doc_type[1:]]
        bill_id = doc_type + bill_num

        title = doc.xpath(
            '//span[text()="Short Description:"]/following-sibling::span[1]/' "text()"
        )[0].strip()
        # 1. Find the heading with "Synopsis As Introduced" for text.
        # 2. Go to the next heading.
        # 3. Backtrack and grab everything to, but not including, #1.
        # 4. Grab text of all, including nested, nodes.
        summary_nodes = doc.xpath(
            '//span[text()="Synopsis As Introduced"]/following-sibling::span[contains(@class, "heading2")]/'
            'preceding-sibling::*[preceding-sibling::span[text()="Synopsis As Introduced"]]//'
            "text()"
        )
        summary = "\n".join([node.strip() for node in summary_nodes])

        bill = Bill(
            identifier=bill_id,
            legislative_session=session,
            title=title,
            classification=bill_type,
            chamber=chamber,
        )

        bill.add_abstract(summary, note="")

        bill.add_source(url)
        # sponsors
        sponsor_list = build_sponsor_list(doc.xpath('//a[contains(@class, "content")]'))
        # don't add just yet; we can make them better using action data

        committee_actors = {}

        # actions
        action_tds = doc.xpath('//a[@name="actions"]/following-sibling::table[1]/td')
        for date, actor, action_elem in group(action_tds, 3):
            date = datetime.datetime.strptime(date.text_content().strip(), "%m/%d/%Y")
            date = self.localize(date).date()
            actor = actor.text_content()
            if actor == "House":
                actor_id = {"classification": "lower"}
            elif actor == "Senate":
                actor_id = {"classification": "upper"}

            action = action_elem.text_content()
            classification, related_orgs = _categorize_action(action)

            # if related_orgs and any(c.startswith("committee") for c in classification):
            #     ((name, source),) = [
            #         (a.text, a.get("href"))
            #         for a in action_elem.xpath("a")
            #         if "committee" in a.get("href")
            #     ]
            #     source = canonicalize_url(source)
            #     actor_id = {"sources__url": source, "classification": "committee"}
            #     committee_actors[source] = name

            bill.add_action(
                action,
                date,
                organization=actor_id,
                classification=classification,
                related_entities=related_orgs,
            )

            if action.lower().find("sponsor") != -1:
                self.refine_sponsor_list(actor, action, sponsor_list, bill_id)

        # now add sponsors
        for spontype, sponsor, chamber, official_type in sponsor_list:
            if spontype == "primary":
                primary = True
            else:
                primary = False
            if chamber:
                bill.add_sponsorship(
                    sponsor, spontype, "person", primary=primary, chamber=chamber
                )
            else:
                bill.add_sponsorship(spontype, sponsor, "person", primary=primary)

        # versions
        version_url = doc.xpath('//a[text()="Full Text"]/@href')[0]
        self.scrape_documents(bill, version_url)
        yield bill

        votes_url = doc.xpath('//a[text()="Votes"]/@href')[0]
        yield from self.scrape_votes(session, bill, votes_url, committee_actors)

    def scrape_documents(self, bill, version_url):
        html = self.get(version_url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(version_url)
        pdf_only = False

        # Some bills don't have html versions, even though they link to them
        # https://ilga.gov/legislation/fulltext.asp?DocName=&
        # SessionId=108&GA=101&DocTypeId=HB&DocNum=66&GAID=15&LegID=113888&SpecSess=&Session=
        # These bills only show one PDF link at a time, so we're safe in the loop below
        if "HTML full text does not exist for this appropriations document" in html:
            pdf_only = True

        for link in doc.xpath('//a[contains(@href, "fulltext")]'):
            name = link.text
            url = link.get("href")

            # Ignore the "Printer-friendly version" link
            # That link is a "latest version" alias for an actual, distinct version
            if "print=true" not in url:
                if name in VERSION_TYPES or "amendment" in name.lower():
                    if pdf_only:
                        # eed to visit the version's page, and get PDF link from there
                        # otherwise get a faulty "latest version"/"LV" alias/duplicate
                        version_page_html = self.get(url).text
                        version_page_doc = lxml.html.fromstring(version_page_html)
                        version_page_doc.make_links_absolute(url)
                        pdf_link = version_page_doc.xpath('//a[text()="PDF"]')[0]
                        url = pdf_link.get("href")
                        mimetype = "application/pdf"
                    else:
                        url = "{}&print=true".format(url)
                        mimetype = "text/html"

                        version_id = re.search(
                            r"DocName=(.*?)&", url, flags=re.IGNORECASE
                        ).group(1)
                        doctype = re.search(
                            r"DocTypeId=(.*?)&", url, flags=re.IGNORECASE
                        ).group(1)
                        # numeric component of the session id
                        session_number = int(
                            "".join(
                                char
                                for char in bill.legislative_session
                                if char.isdigit()
                            )
                        )

                        # if it's html, extract the pdf link too while we're here.
                        pdf_url = f"https://ilga.gov/legislation/{session_number}/{doctype}/PDF/{version_id}.pdf"
                        bill.add_version_link(
                            name, pdf_url, media_type="application/pdf"
                        )

                    bill.add_version_link(name, url, media_type=mimetype)
                elif name in FULLTEXT_DOCUMENT_TYPES:
                    bill.add_document_link(name, url)
                elif "Printer-Friendly" in name:
                    pass
                else:
                    self.warning("unknown document type %s - adding as document" % name)
                    bill.add_document_link(name, url)

    def scrape_votes(self, session, bill, votes_url, committee_actors):
        html = self.get(votes_url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(votes_url)

        for link in doc.xpath('//a[contains(@href, "votehistory")]'):

            if link.get("href") in DUPE_VOTES:
                continue

            pieces = link.text.split(" - ")
            date = pieces[-1]

            vote_type = link.xpath("../ancestor::table[1]//td[1]/text()")[0]
            if vote_type == "Committee Hearing Votes":
                name = re.sub(" *Committee *$", "", pieces[1])
                chamber = link.xpath("../following-sibling::td/text()")[0].lower()
                first_word = name.split()[0]
                try:
                    (source,) = [
                        url
                        for url, committee in committee_actors.items()
                        if committee.startswith(first_word) and chamber in url
                    ]
                    actor = {"sources__url": source, "classification": "committee"}
                except ValueError:
                    self.warning("Can't resolve voting body for %s" % link.get("href"))
                    continue

                # depends on bill type
                motion = "Do Pass"
                if pieces[0].startswith(("SCA", "HCA")):
                    amendment_num = int(re.split(r"SCA|HCA", pieces[0])[-1])
                    amendment = ", Amendment %s" % amendment_num
                    motion += amendment
            else:
                if len(pieces) == 3:
                    motion = pieces[1].strip()
                else:
                    motion = "Third Reading"

                if pieces[0].startswith(("SFA", "HFA")):
                    amendment_num = int(re.split(r"SFA|HFA", pieces[0])[-1])
                    amendment = ", Amendment %s" % amendment_num
                    motion += amendment

                actor = link.xpath("../following-sibling::td/text()")[0]
                if actor == "HOUSE":
                    actor = {"classification": "lower"}
                elif actor == "SENATE":
                    actor = {"classification": "upper"}
                else:
                    self.warning("unknown actor %s" % actor)

            classification, _ = _categorize_action(motion)

            for date_format in ["%b %d, %Y", "%A, %B %d, %Y"]:
                try:
                    date = self.localize(
                        datetime.datetime.strptime(date, date_format)
                    ).date()
                    break
                except ValueError:
                    continue
            else:
                raise AssertionError("Date '{}' does not follow a format".format(date))

            # manual fix for bad bill. TODO: better error catching here
            vote = self.scrape_pdf_for_votes(
                session, actor, date, motion.strip(), link.get("href")
            )
            if vote:
                vote.set_bill(bill)
                yield vote

    def fetch_pdf_lines(self, href):
        # download the file
        try:
            fname, resp = self.urlretrieve(href)
            pdflines = [
                line.decode("utf-8") for line in convert_pdf(fname, "text").splitlines()
            ]
            os.remove(fname)
            return pdflines
        except scrapelib.HTTPError as e:
            assert "404" in e.args[0], "File not found: {}".format(e)
            self.warning("404 error for vote; skipping vote")
            return False

    def scrape_pdf_for_votes(self, session, actor, date, motion, href):
        warned = False
        # vote indicator, a few spaces, a name, newline or multiple spaces
        # VOTE_RE = re.compile('(Y|N|E|NV|A|P|-)\s{2,5}(\w.+?)(?:\n|\s{2})')
        COUNT_RE = re.compile(
            r"^(\d+)\s+YEAS?\s+(\d+)\s+NAYS?\s+(\d+)\s+PRESENT(?:\s+(\d+)\s+NOT\sVOTING)?\s*$"
        )
        PASS_FAIL_WORDS = {
            "PASSED": "pass",
            "PREVAILED": "fail",
            "ADOPTED": "pass",
            "CONCURRED": "pass",
            "FAILED": "fail",
            "LOST": "fail",
        }

        pdflines = self.fetch_pdf_lines(href)

        if not pdflines:
            return False

        yes_count = no_count = present_count = 0
        yes_votes = []
        no_votes = []
        present_votes = []
        excused_votes = []
        not_voting = []
        absent_votes = []
        passed = None
        counts_found = False
        vote_lines = []
        for line in pdflines:
            # consider pass/fail as a document property instead of a result of the vote count
            # extract the vote count from the document instead of just using counts of names
            if not line.strip():
                continue
            elif line.strip() in PASS_FAIL_WORDS:
                # Crash on duplicate pass/fail status that differs from previous status
                if passed is not None and passed != PASS_FAIL_WORDS[line.strip()]:
                    raise Exception("Duplicate pass/fail matches in [%s]" % href)
                passed = PASS_FAIL_WORDS[line.strip()]
            elif COUNT_RE.match(line):
                (yes_count, no_count, present_count, not_voting_count) = COUNT_RE.match(
                    line
                ).groups()
                yes_count = int(yes_count)
                no_count = int(no_count)
                present_count = int(present_count)
                counts_found = True
            elif counts_found:
                for value in VOTE_VALUES:
                    if re.search(r"^\s*({})\s+\w".format(value), line):
                        vote_lines.append(line)
                        break

        votes = find_columns_and_parse(vote_lines)
        for name, vcode in votes.items():
            if name == "Mr. Speaker":
                name = session_details[session]["speaker"]
            elif name == "Mr. President":
                name = session_details[session]["president"]
            else:
                # Converts "Davis,William" to "Davis, William".
                name = re.sub(r"\,([a-zA-Z])", r", \1", name)

            if vcode == "Y":
                yes_votes.append(name)
            elif vcode == "N":
                no_votes.append(name)
            elif vcode == "P":
                present_votes.append(name)
            elif vcode == "E":
                excused_votes.append(name)
            elif vcode == "NV":
                not_voting.append(name)
            elif vcode == "A":
                absent_votes.append(name)

        # fake the counts
        if yes_count == 0 and no_count == 0 and present_count == 0:
            yes_count = len(yes_votes)
            no_count = len(no_votes)
        else:  # audit
            if yes_count != len(yes_votes):
                self.warning(
                    "Mismatched yes count [expect: %i] [have: %i]"
                    % (yes_count, len(yes_votes))
                )
                warned = True
            if no_count != len(no_votes):
                self.warning(
                    "Mismatched no count [expect: %i] [have: %i]"
                    % (no_count, len(no_votes))
                )
                warned = True

        if passed is None:
            if actor["classification"] == "lower":  # senate doesn't have these lines
                self.warning(
                    "No pass/fail word found; fall back to comparing yes and no vote."
                )
                warned = True
            passed = "pass" if yes_count > no_count else "fail"

        classification, _ = _categorize_action(motion)
        vote_event = VoteEvent(
            legislative_session=session,
            motion_text=motion,
            classification=classification,
            organization=actor,
            start_date=date,
            result=passed,
        )
        for name in yes_votes:
            vote_event.yes(name)
        for name in no_votes:
            vote_event.no(name)
        for name in present_votes:
            vote_event.vote("other", name)
        for name in excused_votes:
            vote_event.vote("excused", name)
        for name in not_voting:
            vote_event.vote("not voting", name)
        for name in absent_votes:
            vote_event.vote("absent", name)

        vote_event.set_count("yes", yes_count)
        vote_event.set_count("no", no_count)
        vote_event.set_count("other", present_count)
        vote_event.set_count("excused", len(excused_votes))
        vote_event.set_count("absent", len(absent_votes))
        vote_event.set_count("not voting", len(not_voting))

        vote_event.add_source(href)

        # for distinguishing between votes with the same id and on same day
        vote_event.dedupe_key = href

        if warned:
            self.warning("Warnings were issued. Best to check %s" % href)
        return vote_event

    def refine_sponsor_list(self, chamber, action, sponsor_list, bill_id):
        if action.lower().find("removed") != -1:
            return
        if action.startswith("Chief"):
            self.debug(
                "[%s] Assuming we already caught 'chief' for %s" % (bill_id, action)
            )
            return
        match = SPONSOR_REFINE_PATTERN.match(action)
        if match:
            if match.groupdict()["title"] == "Rep":
                chamber = "lower"
            else:
                chamber = "upper"
            for i, tup in enumerate(sponsor_list):
                spontype, sponsor, this_chamber, otype = tup
                if this_chamber == chamber and sponsor == match.groupdict()["name"]:
                    try:
                        sponsor_list[i] = (
                            SPONSOR_TYPE_REFINEMENTS[match.groupdict()["spontype"]],
                            sponsor,
                            this_chamber,
                            match.groupdict()["spontype"].replace("as ", ""),
                        )
                    except KeyError:
                        self.warning(
                            "[%s] Unknown sponsor refinement type [%s]"
                            % (bill_id, match.groupdict()["spontype"])
                        )
                    return
            self.warning(
                "[%s] Couldn't find sponsor [%s,%s] to refine"
                % (bill_id, chamber, match.groupdict()["name"])
            )
        else:
            self.debug("[%s] Don't know how to refine [%s]" % (bill_id, action))


def find_columns_and_parse(vote_lines):
    columns = find_columns(vote_lines)
    votes = {}
    for line in vote_lines:
        for idx in reversed(columns):
            bit = line[idx:]
            line = line[:idx]
            if bit:
                vote, name = bit.split(" ", 1)
                votes[name.strip()] = vote
    return votes


def _is_potential_column(line, i):
    for val in VOTE_VALUES:
        if re.search(r"^%s\s{2,10}(\w.).*" % val, line[i:]):
            return True
    return False


def find_columns(vote_lines):
    potential_columns = []

    for line in vote_lines:
        pcols = set()
        for i, x in enumerate(line):
            if _is_potential_column(line, i):
                pcols.add(i)
        potential_columns.append(pcols)

    starter = potential_columns[0]
    for pc in potential_columns[1:-1]:
        starter.intersection_update(pc)
    last_row_cols = potential_columns[-1]
    if not last_row_cols.issubset(starter):
        raise Exception(
            "Row's columns [%s] don't align with candidate final columns [%s]: %s"
            % (last_row_cols, starter, line)
        )
    # we should now only have values that appeared in every line
    return sorted(starter)


def build_sponsor_list(sponsor_atags):
    """return a list of (spontype,sponsor,chamber,official_spontype) tuples"""
    sponsors = []
    house_chief = senate_chief = None
    spontype = "cosponsor"
    for atag in sponsor_atags:
        sponsor = atag.text
        if "house" in atag.attrib["href"].split("/"):
            chamber = "lower"
        elif "senate" in atag.attrib["href"].split("/"):
            chamber = "upper"
        else:
            chamber = None
        if chamber == "lower" and house_chief is None:
            spontype = "primary"
            official_spontype = "chief"
            house_chief = sponsor
        elif chamber == "upper" and senate_chief is None:
            spontype = "primary"
            official_spontype = "chief"
            senate_chief = sponsor
        else:
            spontype = "cosponsor"
            official_spontype = "cosponsor"  # until replaced
        sponsors.append((spontype, sponsor, chamber, official_spontype))
    return sponsors
