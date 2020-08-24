import re
import math
import pytz
import datetime
import collections

import lxml.html
from openstates.scrape import Scraper, Bill, VoteEvent
import scrapelib

BASE_URL = "http://www.legislature.mi.gov"
TIMEZONE = pytz.timezone("US/Eastern")


def jres_id(n):
    """ joint res ids go from A-Z, AA-ZZ, etc. """
    return chr(ord("A") + (n - 1) % 25) * (math.floor(n / 26) + 1)


bill_types = {
    "B": "bill",
    "R": "resolution",
    "CR": "concurrent resolution",
    "JR": "joint resolution",
}

bill_chamber_types = {
    "upper": [("SB", 1), ("SR", 1), ("SCR", 1), ("SJR", 1)],
    "lower": [("HB", 4001), ("HR", 1), ("HCR", 1), ("HJR", 1)],
}

_categorizers = {
    "approved by governor with line item(s) vetoed": "executive-veto-line-item",
    "read a first time": "reading-1",
    "read a second time": "reading-2",
    "read a third time": "reading-3",
    "introduced by": "introduction",
    "passed": "passage",
    "referred to committee": "referral-committee",
    "reported": "committee-passage",
    "received": "introduction",
    "presented to governor": "executive-receipt",
    "presented to the governor": "executive-receipt",
    "approved by governor": "executive-signature",
    "approved by the governor": "executive-signature",
    "adopted": "passage",
    "amendment(s) adopted": "amendment-passage",
    "amendment(s) defeated": "amendment-failure",
    "vetoed by governor": "executive-veto",
}


def categorize_action(action):
    for prefix, atype in _categorizers.items():
        if action.lower().startswith(prefix):
            return atype


class MIBillScraper(Scraper):
    def scrape_bill(self, chamber, session, bill_id):
        # try and get bill for the first year of the session biennium
        url = "http://legislature.mi.gov/doc.aspx?%s-%s" % (
            session[:4],
            bill_id.replace(" ", "-"),
        )
        html = self.get(url).text
        # Otherwise, try second year of the session biennium
        if (
            "Page Not Found" in html
            or "The bill you are looking for is not available yet" in html
        ):
            url = "http://legislature.mi.gov/doc.aspx?%s-%s" % (
                session[-4:],
                bill_id.replace(" ", "-"),
            )
            html = self.get(url).text
            if (
                "Page Not Found" in html
                or "The bill you are looking for is not available yet" in html
            ):
                self.warning("Cannot open bill page for {}; skipping".format(bill_id))
                return

        doc = lxml.html.fromstring(html)
        doc.make_links_absolute("http://legislature.mi.gov")

        title = doc.xpath('//span[@id="frg_billstatus_ObjectSubject"]')[
            0
        ].text_content()

        # get B/R/JR/CR part and look up bill type
        bill_type = bill_types[bill_id.split(" ")[0][1:]]

        bill = Bill(bill_id, session, title, chamber=chamber, classification=bill_type)
        bill.add_source(url)

        # sponsors
        sponsors = doc.xpath('//span[@id="frg_billstatus_SponsorList"]/a')
        for sponsor in sponsors:
            name = sponsor.text.replace(u"\xa0", " ")
            # sometimes district gets added as a link
            if name.isnumeric():
                continue

            if len(sponsors) > 1:
                classification = (
                    "primary"
                    if sponsor.tail and "primary" in sponsor.tail
                    else "cosponsor"
                )
            else:
                classification = "primary"
            bill.add_sponsorship(
                name=name.strip(),
                chamber=chamber,
                entity_type="person",
                primary=classification == "primary",
                classification=classification,
            )

        bill.subject = doc.xpath('//span[@id="frg_billstatus_CategoryList"]/a/text()')

        # actions (skip header)
        for row in doc.xpath('//table[@id="frg_billstatus_HistoriesGridView"]/tr')[1:]:
            tds = row.xpath("td")  # date, journal link, action
            date = tds[0].text_content()
            journal = tds[1].text_content()
            action = tds[2].text_content()
            try:
                date = TIMEZONE.localize(datetime.datetime.strptime(date, "%m/%d/%Y"))
            except ValueError:
                self.warning(
                    "{} has action with invalid date. Skipping Action".format(bill_id)
                )
                continue
            # instead of trusting upper/lower case, use journal for actor
            actor = "upper" if "SJ" in journal else "lower"
            classification = categorize_action(action)
            bill.add_action(action, date, chamber=actor, classification=classification)

            # check if action mentions a sub
            submatch = re.search(
                r"WITH SUBSTITUTE\s+([\w\-\d]+)", action, re.IGNORECASE
            )
            if submatch and tds[2].xpath("a"):
                version_url = tds[2].xpath("a/@href")[0]
                version_name = tds[2].xpath("a/text()")[0].strip()
                version_name = "Substitute {}".format(version_name)
                self.info("Found Substitute {}".format(version_url))
                if version_url.lower().endswith(".pdf"):
                    mimetype = "application/pdf"
                elif version_url.lower().endswith(".htm"):
                    mimetype = "text/html"
                bill.add_version_link(version_name, version_url, media_type=mimetype)

            # check if action mentions a vote
            rcmatch = re.search(r"Roll Call # (\d+)", action, re.IGNORECASE)
            if rcmatch:
                rc_num = rcmatch.groups()[0]
                # in format mileg.aspx?page=getobject&objectname=2011-SJ-02-10-011
                journal_link = tds[1].xpath("a/@href")
                if journal_link:
                    objectname = journal_link[0].rsplit("=", 1)[-1]
                    chamber_name = {"upper": "Senate", "lower": "House"}[actor]
                    vote_url = BASE_URL + "/documents/%s/Journal/%s/htm/%s.htm" % (
                        session,
                        chamber_name,
                        objectname,
                    )
                    results = self.parse_roll_call(vote_url, rc_num, session)

                    if results is not None:
                        vote_passed = len(results["yes"]) > len(results["no"])
                        vote = VoteEvent(
                            start_date=date,
                            chamber=actor,
                            bill=bill,
                            motion_text=action,
                            result="pass" if vote_passed else "fail",
                            classification="passage",
                        )

                        # check the expected counts vs actual
                        count = re.search(r"YEAS (\d+)", action, re.IGNORECASE)
                        count = int(count.groups()[0]) if count else 0
                        if count != len(results["yes"]):
                            self.warning(
                                "vote count mismatch for %s %s, %d != %d"
                                % (bill_id, action, count, len(results["yes"]))
                            )
                        count = re.search(r"NAYS (\d+)", action, re.IGNORECASE)
                        count = int(count.groups()[0]) if count else 0
                        if count != len(results["no"]):
                            self.warning(
                                "vote count mismatch for %s %s, %d != %d"
                                % (bill_id, action, count, len(results["no"]))
                            )

                        vote.set_count("yes", len(results["yes"]))
                        vote.set_count("no", len(results["no"]))
                        vote.set_count("other", len(results["other"]))
                        possible_vote_results = ["yes", "no", "other"]
                        for pvr in possible_vote_results:
                            for name in results[pvr]:
                                if session == "2017-2018":
                                    names = name.split("\t")
                                    for n in names:
                                        vote.vote(pvr, name.strip())
                                else:
                                    # Prevents voter names like "House Bill No. 4451, entitled" and other sentences
                                    if len(name.split()) < 5:
                                        vote.vote(pvr, name.strip())
                        vote.add_source(vote_url)
                        yield vote
                else:
                    self.warning("missing journal link for %s %s" % (bill_id, journal))

        # versions
        for row in doc.xpath('//table[@id="frg_billstatus_DocumentGridTable"]/tr'):
            parsed = self.parse_doc_row(row)
            if parsed:
                name, url = parsed
                if url.endswith(".pdf"):
                    mimetype = "application/pdf"
                elif url.endswith(".htm"):
                    mimetype = "text/html"
                bill.add_version_link(name, url, media_type=mimetype)

        # documents
        for row in doc.xpath('//table[@id="frg_billstatus_HlaTable"]/tr'):
            document = self.parse_doc_row(row)
            if document:
                name, url = document
                bill.add_document_link(name, url)
        for row in doc.xpath('//table[@id="frg_billstatus_SfaTable"]/tr'):
            document = self.parse_doc_row(row)
            if document:
                name, url = document
                bill.add_document_link(name, url)

        yield bill

    def scrape(self, chamber=None, session=None):
        if session is None:
            session = self.jurisdiction.legislative_sessions[-1]["identifier"]
            self.info("no session specified, using %s", session)

        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            for abbr, start_num in bill_chamber_types[chamber]:
                n = start_num
                # keep trying bills until scrape_bill returns None
                while True:
                    if "JR" in abbr:
                        bill_id = "%s %s" % (abbr, jres_id(n))
                    else:
                        bill_id = "%s %04d" % (abbr, n)
                    bills = list(self.scrape_bill(chamber, session, bill_id))
                    if not bills:
                        break
                    for bill in bills:
                        yield bill
                    n += 1

    def parse_doc_row(self, row):
        # first anchor in the row is HTML if present, otherwise PDF
        a = row.xpath(".//a")
        if a:
            name = row.xpath(".//b/text()")
            if name:
                name = name[0]
            else:
                name = row.text_content().strip()
            url = a[0].get("href")
            return name, url

    def parse_roll_call(self, url, rc_num, session):
        try:
            resp = self.get(url)
        except scrapelib.HTTPError:
            self.warning(
                "Could not fetch roll call document at %s, unable to extract vote" % url
            )
            return
        html = resp.text
        vote_doc = lxml.html.fromstring(html)
        vote_doc_textonly = vote_doc.text_content()
        if re.search("In\\s+The\\s+Chair", vote_doc_textonly) is None:
            self.warning('"In The Chair" indicator not found, unable to extract vote')
            return

        # split the file into lines using the <p> tags
        pieces = [
            p.text_content().replace(u"\xa0", " ").replace("\r\n", " ")
            for p in vote_doc.xpath("//p")
        ]

        # go until we find the roll call
        for i, p in enumerate(pieces):
            if p.startswith(u"Roll Call No. %s" % rc_num):
                break

        vtype = None
        results = collections.defaultdict(list)

        # once we find the roll call, go through voters
        for p in pieces[i:]:
            # mdash: \xe2\x80\x94 splits Yeas/Nays/Excused/NotVoting
            if "Yeas" in p:
                vtype = "yes"
            elif "Nays" in p:
                vtype = "no"
            elif "Excused" in p or "Not Voting" in p:
                vtype = "other"
            elif "Roll Call No" in p:
                continue
            elif p.startswith("In The Chair:"):
                break
            elif vtype:
                # split on multiple spaces not preceeded by commas
                for line in re.split(r"(?<!,)\s{2,}", p):
                    if line.strip():
                        if session == "2017-2018":
                            for leg in line.split():
                                results[vtype].append(leg)
                        else:
                            results[vtype].append(line)
            else:
                self.warning("piece without vtype set: %s", p)

        return results
