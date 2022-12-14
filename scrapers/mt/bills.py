import os
import re
import itertools
import copy
import tempfile
import urllib
from datetime import datetime
from collections import defaultdict

from openstates.scrape import Scraper, Bill, VoteEvent
from openstates.utils import convert_pdf
from scrapelib import HTTPError

import lxml.html

from utils import LXMLMixin
from . import actions

# from https://stackoverflow.com/questions/38015537/python-requests-exceptions-sslerror-dh-key-too-small
import requests

requests.packages.urllib3.disable_warnings()
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ":HIGH:!DH:!aNULL"


actor_map = {
    "(S)": "upper",
    "(H)": "lower",
    "(C)": "legislature",  # TODO: add clerk role?
}

sponsor_map = {"Primary Sponsor": "primary"}

vote_passage_indicators = [
    "Adopted",
    "Appointed",
    "Carried",
    "Concurred",
    "Dissolved",
    "Passed",
    "Rereferred to Committee",
    "Transmitted to",
    "Veto Overidden",
    "Veto Overridden",
]
vote_failure_indicators = ["Failed", "Rejected"]
vote_ambiguous_indicators = [
    "Indefinitely Postponed",
    "On Motion Rules Suspended",
    "Pass Consideration",
    "Reconsidered Previous",
    "Rules Suspended",
    "Segregated from Committee",
    "Special Action",
    "Sponsor List Modified",
    "Tabled",
    "Taken from",
]


class MTBillScraper(Scraper, LXMLMixin):
    def __init__(self, *args, **kwargs):
        super(MTBillScraper, self).__init__(*args, **kwargs)

        self._seen_vote_ids = set()

        self.search_url_template = (
            "http://laws.leg.mt.gov/laws%s/LAW0203W$BSRV.ActionQuery?"
            "P_BLTP_BILL_TYP_CD=%s&P_BILL_NO=%s&P_BILL_DFT_NO=&"
            "Z_ACTION=Find&P_SBJ_DESCR=&P_SBJT_SBJ_CD=&P_LST_NM1=&"
            "P_ENTY_ID_SEQ="
        )

    def scrape(self, chamber=None, session=None):
        # set default parameters
        chambers = [chamber] if chamber else ["upper", "lower"]

        # self.versions_dict = self._versions_dict(session)
        details = next(
            each
            for each in self.jurisdiction.legislative_sessions
            if each["identifier"] == session
        )
        session_name = details["_scraped_name"]

        bills_url = (
            "http://laws.leg.mt.gov/legprd/LAW0217W$BAIV.return_all_bills?P_SESS={}"
        ).format(session_name)
        bills_page = self.lxmlize(bills_url)

        bills = []
        for bill_row in bills_page.xpath("//tr"):
            bill_url_hrefs = bill_row.xpath(
                'td/a[contains(@href, "ActionQuery")]/@href'
            )
            if len(bill_url_hrefs) == 0:
                continue  # no URL in this TR, so ignore it

            bill_url = bill_url_hrefs[0]
            sponsor_results = bill_row.xpath("td[3]/text()")
            if len(sponsor_results) > 0:
                sponsor = sponsor_results[0]
            else:
                sponsor = ""

            if "lower" in chambers and (
                "HB" in bill_url or "HJ" in bill_url or "HR" in bill_url
            ):
                bills.append({"url": bill_url, "sponsor": sponsor})
            if "upper" in chambers and (
                "SB" in bill_url or "SJ" in bill_url or "SR" in bill_url
            ):
                bills.append({"url": bill_url, "sponsor": sponsor})
            if "LC" in bill_url and "BILL_NO" not in bill_url:
                # this is a bill proposal, not an actual bill, aka "unintroduced" bill
                # unintroduced bills don't exactly have a chamber, but we'll use sponsor's chamber to assign one
                bills.append({"url": bill_url, "sponsor": sponsor})

        for bill_info in bills:
            bill, votes = self.parse_bill(
                bill_info["url"], bill_info["sponsor"], session
            )
            yield bill
            for vote in votes:
                if vote.dedupe_key not in self._seen_vote_ids:
                    self._seen_vote_ids.add(vote.dedupe_key)
                    yield vote

    def parse_bill(self, bill_url, list_sponsor, session):
        # list_sponsor passed to support proposed bills (aka "unintroduced") which have "LC XXXX" bill numbers
        bill = None
        doc = self.lxmlize(bill_url)

        bill, votes = self.parse_bill_status_page(bill_url, doc, list_sponsor, session)

        # Get versions on the detail page.
        versions = [
            a["description"]
            for a in bill.actions
            if "Version Available" in a["description"]
        ]
        if not versions:
            version_name = "Introduced"
        else:
            version = versions.pop()
            if "New Version" in version:
                version_name = "Amended"
            elif "Enrolled" in version:
                version_name = "Enrolled"

        # self.add_other_versions(bill)

        # Add pdf.
        pdf_urls = set(doc.xpath('//a/@href[contains(., "billpdf")]'))
        if len(pdf_urls) > 0:
            url = pdf_urls.pop()
            url = url.replace("http:", "https:")
            bill.add_version_link(version_name, url, media_type="application/pdf")

        new_versions_url = doc.xpath('//a[text()="Previous Version(s)"]/@href')
        if new_versions_url:
            self.scrape_new_site_versions(bill, new_versions_url[0])

        # Add bill url as a source.
        bill.add_source(bill_url)

        return bill, votes

    def scrape_new_site_versions(self, bill, url):
        page = self.lxmlize(url)
        for link in page.xpath('//div[contains(@class,"container white")]/a'):
            link_text = link.xpath("text()")[0].strip()
            link_url = link.xpath("@href")[0]
            link_url = link_url.replace("http:", "https:")
            bill.add_version_link(
                link_text, link_url, media_type="application/pdf", on_duplicate="ignore"
            )

    def _get_tabledata(self, status_page):
        """Montana doesn't currently list co/multisponsors on any of the
        legislation I've seen. So this function only adds the primary
        sponsor."""
        tabledata = defaultdict(list)
        join = " ".join

        # Get the top data table.
        for tr in status_page.xpath("//tr"):
            tds = tr.xpath("td")
            try:
                key = tds[0].text_content().lower()
                if key == "primary sponsor:":
                    val = re.sub(r"[\s]+", " ", tds[1].xpath("./a/text()")[0])
                else:
                    val = join(tds[1].text_content().strip().split())
            except IndexError:
                continue
            if not key.startswith("("):
                tabledata[key].append(val)

        return dict(tabledata)

    def parse_bill_status_page(self, url, page, list_sponsor, session):
        # list_sponsor passed in to support proposed bills (aka "unintroduced") which have "LC XXXX" bill numbers
        # see 2007 HB 2... weird.
        parsed_url = urllib.parse.urlparse(url)
        parsed_query = dict(urllib.parse.parse_qsl(parsed_url.query))
        if "P_BLTP_BILL_TYP_CD" in parsed_query:
            # normal bill
            bill_id = "{0} {1}".format(
                parsed_query["P_BLTP_BILL_TYP_CD"], parsed_query["P_BILL_NO1"]
            )
        elif "P_BILL_DFT_NO5" in parsed_query:
            # proposed bill ("unintroduced")
            bill_id = "{0} {1}".format(
                parsed_query["P_BILL_DFT_NO5"][0:2],
                parsed_query["P_BILL_DFT_NO5"][2:6].lstrip("0"),
            )

        try:
            xp = '//b[text()="Short Title:"]/../following-sibling::td/text()'
            title = page.xpath(xp).pop()
        except IndexError:
            title = page.xpath("//tr[1]/td[2]")[0].text_content()

        # Add bill type.
        _bill_id = bill_id.lower()
        if "b" in _bill_id:
            classification = "bill"
        elif "j" in _bill_id or "jr" in _bill_id:
            classification = "joint resolution"
        elif "cr" in _bill_id:
            classification = "concurrent resolution"
        elif "r" in _bill_id:
            classification = "resolution"
        elif "lc" in _bill_id:
            classification = "proposed bill"

        # chamber
        if _bill_id[0] == "h":
            chamber = "lower"
        elif _bill_id[0] == "s":
            chamber = "upper"
        else:
            # fall back to using the sponsor's chamber
            # used for proposed bills aka unintroducd aka LC bills
            if " HD " in list_sponsor:
                chamber = "lower"
            if " SD " in list_sponsor:
                chamber = "upper"
            else:
                # a true fallback: some sponsors are organizations eg "Economic Affairs Interim Committee"
                chamber = "legislature"

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=title,
            classification=classification,
        )

        self.add_actions(bill, page)
        votes = self.add_votes(bill, page, url)

        tabledata = self._get_tabledata(page)

        # Add sponsor info.
        if "primary sponsor:" in tabledata and tabledata["primary sponsor:"][0]:
            bill.add_sponsorship(
                tabledata["primary sponsor:"][0],
                classification="primary",
                entity_type="person",
                primary=True,
            )
        elif "(" in list_sponsor:
            # use sponsor data from the bill listing, if it contains a party designation eg (R)
            # used for proposed bills aka unintroducd aka LC bills
            # grab everything before " (R) SD 30" in "John Esp (R) SD 30"
            sponsor_name_raw = re.search(r"(.+) \(", list_sponsor)[1]
            sponsor_name_raw = " ".join(
                sponsor_name_raw.split()
            )  # eliminate extra whitespace in middle of name parts
            if sponsor_name_raw:
                bill.add_sponsorship(
                    sponsor_name_raw,
                    classification="primary",
                    entity_type="person",
                    primary=True,
                )
        elif "lc" in _bill_id:
            # probably the sponsor is an organization eg a committee, because LC bills can be sponsored by orgs
            # so just use the sponsor as listed from the index page
            if list_sponsor:
                bill.add_sponsorship(
                    list_sponsor,
                    classification="primary",
                    entity_type="organization",
                    primary=True,
                )

        # A various plus fields MT provides.
        plus_fields = [
            "requester",
            ("chapter number:", "chapter"),
            "transmittal date:",
            "drafter",
            "fiscal note probable:",
            "bill draft number:",
            "preintroduction required:",
            "by request of",
            "category:",
        ]

        for x in plus_fields:
            if isinstance(x, tuple):
                _key, key = x
            else:
                _key = key = x
                key = key.replace(" ", "_")

            try:
                val = tabledata[_key]
            except KeyError:
                continue

            if len(val) == 1:
                val = val[0]

            bill.extras[key] = val

        # Add bill subjects.
        xp = '//th[contains(., "Revenue/Approp.")]/ancestor::table/tr'
        subjects = []
        for tr in page.xpath(xp):
            try:
                subj = tr.xpath("td")[0].text_content()
            except IndexError:
                continue
            subjects.append(subj)

        for s in subjects:
            bill.add_subject(s)

        self.add_fiscal_notes(page, bill)

        return bill, list(votes)

    def add_actions(self, bill, status_page):
        for idx, action in enumerate(
            reversed(
                status_page.xpath(
                    '//form[contains(@action, "BLAC.QueryList")]//table/tr'
                )[1:]
            )
        ):
            try:
                actor = actor_map[action.xpath("td[1]")[0].text_content().split(" ")[0]]
                action_name = (
                    action.xpath("td[1]")[0]
                    .text_content()
                    .replace(actor, "")[4:]
                    .strip()
                )
            except KeyError:
                action_name = action.xpath("td[1]")[0].text_content().strip()
                actor = (
                    "legislature" if action_name == "Chapter Number Assigned" else ""
                )

            action_name = action_name.replace("&nbsp", "")
            action_date = datetime.strptime(
                action.xpath("td[2]")[0].text, "%m/%d/%Y"
            ).date()
            action_type = actions.categorize_actions(action_name)

            # grab committees here
            try:
                committee = action.xpath("td[5]")[0].text_content().strip()
                committee = re.sub(r"&nbsp", "", committee)
                if committee != "":
                    # include parenthesis?
                    # committee = re.search(r"\([A-Z]\)\s(.+)", committee).groups()[0]
                    action_name += " - "
                    action_name += committee
            except KeyError:
                pass

            if "by senate" in action_name.lower():
                actor = "upper"

            bill.add_action(
                action_name,
                action_date,
                classification=action_type,
                chamber=actor,
            )

    def _versions_dict(self, session):
        """Get a mapping of ('HB', '2') tuples to version urls."""

        res = defaultdict(dict)

        url = "https://leg.mt.gov/laws/bills/{}/BillPdf/".format(session)

        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        for url in doc.xpath('//a[contains(@href, "/bills/")]/@href')[1:]:
            doc = self.lxmlize(url)
            for fn in doc.xpath("//a/@href")[1:]:
                _url = urllib.parse.urljoin(url, fn)
                fn = fn.split("/")[-1]
                m = re.search(r"([A-Z]+)0*(\d+)_?(.*?)\.pdf", fn)
                if m:
                    type_, id_, version = m.groups()
                    res[(type_, id_)][version] = _url

        return res

    def add_other_versions(self, bill):

        count = itertools.count(1)
        xcount = itertools.chain([1], itertools.count(1))
        type_, id_ = bill.identifier.split()
        version_urls = copy.copy(self.versions_dict[(type_, id_)])
        mimetype = "application/pdf"
        version_strings = [
            "Introduced Bill Text Available Electronically",
            "Printed - New Version Available",
            "Clerical Corrections Made - New Version Available",
        ]

        if bill.title == "General Appropriations Act":
            # Need to special-case this one
            # According to its versions page,
            # > Because it contains many tables that are not well rendered with HTML,
            # > HB2 is available electronically only in Adobe Portable Document Format (PDF).
            return

        for i, a in enumerate(bill.actions):
            text = a["description"]
            if text in version_strings:
                name = bill.actions[i - 1]["description"]

                if "Clerical Corrections" in text:
                    name += " (clerical corrections made)"
                try:
                    url = version_urls.pop(str(next(count)))
                    url = url.replace("http:", "https:")
                except KeyError:
                    msg = "No url found for version: %r" % name
                    self.warning(msg)
                else:
                    if "Introduced Bill" in text:
                        name = "Introduced"
                    bill.add_version_link(name, url, media_type=mimetype)
                    continue

                try:
                    url = version_urls["x" + str(next(xcount))]
                    url = url.replace("http:", "https:")
                except KeyError:
                    continue

                name = actions[i - 1]["action"]
                bill.add_version_link(name, url, media_type=mimetype)

    def add_votes(self, bill, status_page, status_url):
        """For each row in the actions table that links to a vote,
        retrieve the vote object created by the scraper in add_actions
        and update the vote object with the voter data.
        """
        base_url, _, _ = status_url.rpartition("/")
        base_url += "/"
        status_page.make_links_absolute(base_url)

        for tr in status_page.xpath("//table")[3].xpath("tr")[2:]:
            tds = list(tr)

            if tds:
                vote_url = tds[2].xpath("a/@href")

                if vote_url:

                    # Get the matching vote object.
                    text = tr.itertext()
                    action = next(text).strip()
                    chamber, action = action.split(" ", 1)
                    date = datetime.strptime(next(text), "%m/%d/%Y").date()
                    vote_url = vote_url[0]

                    chamber = actor_map[chamber]
                    vote = dict(
                        chamber=chamber, date=date, action=action, vote_url=vote_url
                    )

                    # Update the vote object with voters..
                    vote = self._parse_votes(vote_url, vote, bill)
                    if vote:
                        yield vote

    def _parse_votes(self, url, vote, bill):
        """Given a vote url and a vote object, extract the voters and
        the vote counts from the vote page and update the vote object.
        """
        if url.lower().endswith(".pdf"):

            try:
                resp = self.get(url)
            except HTTPError:
                # This vote document wasn't found.
                msg = "No document found at url %r" % url
                self.logger.warning(msg)
                return

            try:
                v = PDFCommitteeVote(url, resp.content, bill)
                return v.asvote()
            except PDFCommitteeVoteParseError:
                # Warn and skip.
                self.warning("Could't parse committee vote at %r" % url)
                return

        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        # Yes, no, excused, absent.
        try:
            vals = doc.xpath("//table")[1].xpath("tr/td/text()")
        except IndexError:
            # Most likely was a bogus link lacking vote data.
            return

        yes_count, no_count, excused_count, absent_count = map(int, vals)

        # Get the motion.
        try:
            motion = doc.xpath("//br")[-1].tail.strip()
        except IndexError:
            # Some of them mysteriously have no motion listed.
            motion = vote["action"]

        if not motion:
            motion = vote["action"]

        vote["motion"] = motion

        action = vote["action"]
        vote_url = vote["vote_url"]

        vote = VoteEvent(
            chamber=vote["chamber"],
            start_date=vote["date"],
            motion_text=vote["motion"],
            result="fail",  # placeholder
            classification="passage",
            bill=bill,
            bill_action=vote["action"],
        )
        vote.dedupe_key = vote_url  # URL contains sequence number
        vote.add_source(vote_url)
        vote.set_count("yes", yes_count)
        vote.set_count("no", no_count)
        vote.set_count("excused", excused_count)
        vote.set_count("absent", absent_count)

        for text in doc.xpath("//table")[2].xpath("tr/td/text()"):
            if not text.strip("\xa0"):
                continue
            v, name = filter(None, text.split("\xa0"))
            # Considering Name is brackets as short name
            regex = re.compile(r".*?\((.*?)\)")
            short_name = re.findall(regex, name)
            if len(short_name) > 0:
                note = "Short Name: " + short_name[0]
            else:
                note = ""
            # Name without brackets like 'Kary, Douglas'
            name = re.sub(r"[\(\[].*?[\)\]]", "", name)
            if v == "Y":
                vote.yes(name, note=note)
            elif v == "N":
                vote.no(name, note=note)
            elif v == "E":
                vote.vote("excused", name, note=note)
            elif v == "A":
                vote.vote("absent", name, note=note)

        # code to determine value of `passed`
        passed = None

        # some actions take a super majority, so we aren't just
        # comparing the yeas and nays here.
        for i in vote_passage_indicators:
            if i in action:
                passed = True
                break
        for i in vote_failure_indicators:
            if i in action and passed:
                # a quick explanation:  originally an exception was
                # thrown if both passage and failure indicators were
                # present because I thought that would be a bug in my
                # lists.  Then I found 2007 HB 160.
                # Now passed = False if the nays outnumber the yays..
                # I won't automatically mark it as passed if the yays
                # ounumber the nays because I don't know what requires
                # a supermajority in MT.
                if no_count >= yes_count:
                    passed = False
                    break
                else:
                    raise Exception(
                        "passage and failure indicator" "both present at: %s" % url
                    )
            if i in action and passed is None:
                passed = False
                break
        for i in vote_ambiguous_indicators:
            if i in action:
                passed = yes_count > no_count
                break
        if passed is None:
            raise Exception("Unknown passage at: %s" % url)

        vote.result = "pass" if passed else "fail"

        return vote

    def add_fiscal_notes(self, doc, bill):

        for link in doc.xpath('//a[contains(text(), "Fiscal Note")]'):
            bill.add_document_link(
                link.text_content().strip(),
                link.attrib["href"],
                media_type="application/pdf",
            )


class PDFCommitteeVoteParseError(Exception):
    pass


class PDFCommitteeVote404Error(PDFCommitteeVoteParseError):
    pass


class PDFCommitteeVote(object):
    def __init__(self, url, resp, bill):
        self.url = url
        self.bill = bill

        # Fetch the document and put it into tempfile.
        fd, filename = tempfile.mkstemp()

        with open(filename, "wb") as f:
            f.write(resp)

        # Convert it to text.
        try:
            text = convert_pdf(filename, type="text")
        except Exception:
            msg = "couldn't convert pdf."
            raise PDFCommitteeVoteParseError(msg)

        # Get rid of the temp file.
        os.close(fd)
        os.remove(filename)

        if not text.strip():
            msg = "PDF file was empty."
            raise PDFCommitteeVoteParseError(msg)

        self.text = "\n".join([line.decode() for line in text.splitlines() if line])

    def committee(self):
        """
        XXX: OK. So, the error here:


            When we have a `joint' chamber vote, we also need the committee
            attached with the bill, or the OCD conversion won't know which
            committee on the whole to associate with.

            In addition, matching to the COW is wrong; since this was a
            committee vote. I'm stubbing this out since the site is currently
            offline
        """
        raise NotImplementedError

    def chamber(self):
        chamber_dict = {"HOUSE": "lower", "SENATE": "upper", "JOINT": "legislature"}
        chamber = re.search(r"(HOUSE|SENATE|JOINT)", self.text)
        if chamber is None:
            raise PDFCommitteeVoteParseError("PDF didn't have chamber on it")
        return chamber_dict[chamber.group(1)]

    def date(self):

        months = """january february march april may june july
            august september october november december""".split()

        text = iter(self.text.splitlines())

        line = next(text).strip()
        while True:

            _line = line.lower()
            break_outer = False
            for m in months:
                if m in _line:
                    break_outer = True
                    break

            if break_outer:
                break

            try:
                line = next(text).strip()
            except StopIteration:
                msg = "Couldn't parse the vote date."
                raise PDFCommitteeVoteParseError(msg)

        try:
            return datetime.strptime(line, "%B %d, %Y").date()
        except ValueError:
            raise PDFCommitteeVoteParseError("Could't parse the vote date.")

    def motion(self):

        text = iter(self.text.splitlines())

        while True:
            line = next(text)
            if "VOTE TABULATION" in line:
                break

        line = next(text)
        _, motion = line.split(" - ")
        motion = motion.strip()
        return motion

    def _getcounts(self):
        m = re.search(r"YEAS \- .+$", self.text, re.MULTILINE)
        if m:
            x = m.group()
        else:
            msg = "Couldn't find vote counts."
            raise PDFCommitteeVoteParseError(msg)
        self._counts_data = dict(re.findall(r"(\w+) - (\d+)", x))

    def yes_count(self):
        if not hasattr(self, "_counts_data"):
            self._getcounts()
        return int(self._counts_data["YEAS"])

    def no_count(self):
        if not hasattr(self, "_counts_data"):
            self._getcounts()
        return int(self._counts_data["NAYS"])

    def other_count(self):
        return len(self.other_votes())

    def _getvotes(self):
        junk = ["; by Proxy"]
        res = defaultdict(list)
        data = re.findall(r"([A-Z]) {6,7}(.+)", self.text, re.MULTILINE)
        for val, name in data:
            for j in junk:
                name = name.replace(j, "")
            res[val].append(name)
        self._votes_data = res

    def yes_votes(self):
        if not hasattr(self, "_votes_data"):
            self._getvotes()
        return self._votes_data["Y"]

    def other_votes(self):
        if not hasattr(self, "_votes_data"):
            self._getvotes()
        return self._votes_data["--"]

    def no_votes(self):
        if not hasattr(self, "_votes_data"):
            self._getvotes()
        return self._votes_data["N"]

    def passed(self):
        return self.no_count() < self.yes_count()

    def asvote(self):
        v = VoteEvent(
            chamber=self.chamber(),
            start_date=self.date(),
            motion_text=self.motion(),
            result="pass" if self.passed() else "fail",
            classification="passage",
            bill=self.bill,
        )
        v.dedupe_key = self.url  # URL contains sequence number
        v.set_count("yes", self.yes_count())
        v.set_count("no", self.no_count())
        v.set_count("other", self.other_count())

        for voter in self.yes_votes():
            v.yes(voter)
        for voter in self.no_votes():
            v.no(voter)
        for voter in self.other_votes():
            v.vote("other", voter)
        v.add_source(self.url)
        return v
