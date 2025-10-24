import dateutil
import re
import lxml.html
import scrapelib
import collections
from datetime import date
from utils.media import get_media_type

from openstates.scrape import Scraper, Bill, VoteEvent

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
BASE_URL = "https://legislature.mi.gov"


def categorize_action(action: str) -> str:
    for prefix, atype in _categorizers.items():
        if action.lower().startswith(prefix):
            return atype


class MIBillScraper(Scraper):
    headers = {}

    # convert from MI's redirector to a bill permalink
    def make_bill_url(self, url: str) -> str:
        match = re.search(r"objectName=(.*)&", url)
        return f"https://legislature.mi.gov/Bills/Bill?ObjectName={match.group(1)}"

    def scrape(self, session):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/118.0"
        }
        search_url = f"https://legislature.mi.gov/Search/ExecuteSearch?chamber=&docTypesList=HB%2CSB&docTypesList=HR%2CSR&docTypesList=HCR%2CSCR&docTypesList=HJR%2CSJR&sessions={session}&sponsor=&number=&dateFrom=&dateTo=&contentFullText="
        page = self.get(search_url, headers=self.headers).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(search_url)

        for link in page.xpath(
            "//div[contains(@class,'tableScrollWrapper')]/table[1]/tbody/tr/td[1]/a"
        ):
            bill_url = self.make_bill_url(link.xpath("@href")[0])
            bill_id = link.xpath("text()")[0].split(" of ")[0]
            yield from self.scrape_bill(session, bill_id, bill_url)

    def scrape_bill(self, session: str, bill_id: str, url: str) -> None:
        page = self.get(url, headers=self.headers).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        title = page.xpath("string(//div[@id='ObjectSubject'])").strip()

        heading = page.xpath("//h1[@id='BillHeading']/text()")[0].lower()

        if "house" in heading:
            chamber = "lower"
        elif "senate" in heading:
            chamber = "upper"
        elif "join" in heading:
            chamber = "joint"

        bill_type = "bill"
        for key in ["concurrent resolution", "joint resolution", "resolution"]:
            if key in heading:
                bill_type = key

        bill = Bill(bill_id, session, title, chamber=chamber, classification=bill_type)

        bill.add_source(url)

        self.scrape_actions(bill, page)
        self.scrape_legal(bill, page)
        self.scrape_sponsors(bill, page)
        self.scrape_subjects(bill, page)
        self.scrape_versions(bill, page)
        yield from self.scrape_votes(bill, page)
        yield bill

    def scrape_actions(self, bill: Bill, page: lxml.html.HtmlElement):
        # there can be multiple substitute printings with the same name,
        # but different text
        seen_subs = {}
        for row in page.xpath("//div[@id='History']/table/tbody/tr"):
            when = row.xpath("td[1]/text()")[0]
            when = dateutil.parser.parse(when).date()

            action = row.xpath("string(td[3])").strip()

            journal = row.xpath("string(td[2])").strip()

            if "HJ" in journal:
                actor = "lower"
            elif "SJ" in journal:
                actor = "upper"

            bill.add_action(
                action, when, chamber=actor, classification=categorize_action(action)
            )

            if "substitute" in action.lower() and row.xpath("td[3]/a/@href"):
                version_url = row.xpath("td[3]/a/@href")[0]
                sub = re.search(r"\(.*?\)", action)

                if sub:
                    version_name = f"Substitute {sub.group(0)}"
                elif "committee of the whole" in action.lower():
                    version_name = "Substitute, reported by Committee of the Whole"

                if version_name in seen_subs:
                    seen_subs[version_name] += 1
                    version_name = f"{version_name} - {seen_subs[version_name]}"
                else:
                    seen_subs[version_name] = 1
                self.info(f"Found Substitute {version_name}, {version_url}")
                bill.add_version_link(
                    version_name,
                    version_url,
                    media_type=get_media_type(version_url, default="text/html"),
                    on_duplicate="ignore",
                )

            # chapter law
            if "assigned pa" in action.lower():
                match = re.search(r"(\d+)'(\d+)", action)
                act_num = match.group(1).lstrip("0")
                act_year = f"20{match.group(2)}"
                bill.add_citation(
                    "Michigan Public Acts",
                    f"Public Act {act_num} of {act_year}",
                    citation_type="chapter",
                )

    def scrape_votes(self, bill: Bill, page: lxml.html.HtmlElement):

        # Iterate through vote history table rows
        for row in page.xpath("//div[@id='History']/table/tbody/tr"):
            # Extract vote metadata
            when = row.xpath("td[1]/text()")[0]
            when = dateutil.parser.parse(when).date()
            action = row.xpath("string(td[3])").strip()
            journal = row.xpath("string(td[2])").strip()

            # Determine chamber from journal reference
            if "HJ" in journal:
                actor = "lower"
            elif "SJ" in journal:
                actor = "upper"

            # Process roll call votes
            rcmatch = re.search(r"Roll Call # (\d+)", action, re.IGNORECASE)
            if rcmatch:
                rc_num = rcmatch.groups()[0]
                vote_url = None
                journal_link = None

                # In format: mileg.aspx?page=getobject&objectname=2011-SJ-02-10-011
                journal_link = row.xpath("td[2]/a/@href")
                chamber_name = {"upper": "Senate", "lower": "House"}[actor]

                # Build vote URL from journal link or generate fallback
                if journal_link:
                    objectname = journal_link[0].rsplit("=", 1)[-1]
                    vote_url = BASE_URL + "/documents/%s/Journal/%s/htm/%s.htm" % (
                        bill.legislative_session,
                        chamber_name,
                        objectname,
                    )
                else:
                    self.warning(
                        f"Missing journal link for {bill.identifier} {action}, Trying to generate it using journal reference {journal}"
                    )
                    vote_url = (
                        self.make_michigan_votes_url_when_journal_link_not_available(
                            action_date=when,
                            journal_reference=journal,
                            base_url=BASE_URL,
                            legislative_session=bill.legislative_session,
                            chamber=chamber_name,
                        )
                    )

                # Parse and validate vote results
                results = self.parse_roll_call(
                    vote_url, rc_num, bill.legislative_session
                )

                if results is not None:
                    vote_passed = len(results["yes"]) > len(results["no"])
                    vote = VoteEvent(
                        start_date=when,
                        chamber=actor,
                        bill=bill,
                        motion_text=action,
                        result="pass" if vote_passed else "fail",
                        classification="passage",
                    )

                    # Verify vote count matching the expected count in the action string
                    count = re.search(r"YEAS (\d+)", action, re.IGNORECASE)
                    count = int(count.groups()[0]) if count else 0
                    if count != len(results["yes"]):
                        self.warning(
                            "vote count mismatch for %s %s, %d != %d"
                            % (bill.identifier, action, count, len(results["yes"]))
                        )

                    count = re.search(r"NAYS (\d+)", action, re.IGNORECASE)
                    count = int(count.groups()[0]) if count else 0
                    if count != len(results["no"]):
                        self.warning(
                            "vote count mismatch for %s %s, %d != %d"
                            % (bill.identifier, action, count, len(results["no"]))
                        )

                    vote.set_count("yes", len(results["yes"]))
                    vote.set_count("no", len(results["no"]))
                    vote.set_count("other", len(results["other"]))
                    possible_vote_results = ["yes", "no", "other"]
                    for pvr in possible_vote_results:
                        for name in results[pvr]:
                            if bill.legislative_session == "2017-2018":
                                names = name.split("\t")
                                for n in names:
                                    vote.vote(pvr, n.strip())
                            else:
                                # Prevents voter names like "House Bill No. 4451, entitled" and other sentences
                                if len(name.split()) < 5:
                                    vote.vote(pvr, name.strip())

                    vote.add_source(vote_url)
                    yield vote

    def make_michigan_votes_url_when_journal_link_not_available(
        self,
        action_date: date,
        journal_reference: str,
        base_url: str,
        legislative_session: str,
        chamber: str,
    ) -> str:

        journal_match = re.search(r"[HS]J\s+(\d+)", journal_reference)
        if not journal_match:
            self.warning(f"Could not extract journal number from '{journal_reference}'")
            return None

        if not isinstance(action_date, date):
            self.warning(
                f"Invalid action_date while generating vote url: {action_date}, must be a datetime.date object"
            )
            return None

        journal_num = journal_match.group(1).zfill(3)
        date_formatted = action_date.strftime("%m-%d")
        journal_prefix = "SJ" if chamber == "Senate" else "HJ"
        year = str(action_date.year)
        objectname = f"{year}-{journal_prefix}-{date_formatted}-{journal_num}"
        return f"{base_url}/documents/{legislative_session}/Journal/{chamber}/htm/{objectname}.htm"

    def parse_roll_call(self, url, rc_num, session):
        try:
            resp = self.get(url, headers=self.headers)
        except scrapelib.HTTPError:
            self.warning(
                f"Could not fetch roll call document at {url}, unable to extract vote"
            )
            return
        html = resp.text
        vote_doc = lxml.html.fromstring(html)
        vote_doc_textonly = vote_doc.text_content()

        if re.search("In\\s+The\\s+Chair", vote_doc_textonly) is None:
            self.warning('"In The Chair" indicator not found, unable to extract vote')
            return

        # Split the file into lines using the <p> tags
        pieces = [
            p.text_content().replace("\xa0", " ").replace("\r\n", " ")
            for p in vote_doc.xpath("//p")
        ]

        # Go until we find the roll call
        for i, p in enumerate(pieces):
            if p.startswith(f"Roll Call No. {rc_num}"):
                break

        vtype = None
        results = collections.defaultdict(list)

        # Once we find the roll call, go through voters
        for p in pieces[i:]:
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
                # Split on multiple spaces not preceded by commas
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

    def scrape_legal(self, bill: Bill, page: lxml.html.HtmlElement):
        for row in page.xpath(
            "//div[@id='ObjectSubject']/a[contains(@href,'?sectionNumbers')]/text()"
        ):
            bill.add_citation(
                "Michigan Compiled Laws", f"MCL {row.strip()}", citation_type="proposed"
            )

    def scrape_sponsors(self, bill: Bill, page: lxml.html.HtmlElement):
        for row in page.xpath(
            "//li[contains(@title, 'sponsored')]/a[contains(@class,'primarySponsor')]"
        ):
            sponsor = row.xpath("text()")[0].split("(")[0].strip()
            bill.add_sponsorship(
                sponsor, classification="primary", entity_type="person", primary=True
            )

        for row in page.xpath(
            "//li[contains(@title, 'sponsored')]/a[not(contains(@class,'primarySponsor'))]"
        ):
            sponsor = row.xpath("text()")[0].split("(")[0].strip()
            bill.add_sponsorship(
                sponsor, classification="cosponsor", entity_type="person", primary=False
            )

    def scrape_subjects(self, bill: Bill, page: lxml.html.HtmlElement):
        # union with the second expression is just in case they fix the typo
        for row in page.xpath(
            "//div[@id='CateogryList']/a|//div[@id='CategoryList']/a"
        ):
            bill.add_subject(row.xpath("text()")[0].strip())

    def scrape_versions(self, bill: Bill, page: lxml.html.HtmlElement):
        for row in page.xpath("//div[@class='billDocuments']/div[@class='billDocRow']"):
            name = row.xpath(".//div[@class='text']/span/strong/text()")[0]
            if row.xpath(".//div[@class='pdf']/a/@href"):
                bill.add_version_link(
                    name,
                    row.xpath(".//div[@class='pdf']/a/@href")[0],
                    media_type="application/pdf",
                    on_duplicate="ignore",
                )
            if row.xpath(".//div[@class='html']/a/@href"):
                bill.add_version_link(
                    name,
                    row.xpath(".//div[@class='html']/a/@href")[0],
                    media_type="text/html",
                    on_duplicate="ignore",
                )

        for row in page.xpath(
            "//div[@id='HFAAnalysisSection']/div/div[@class='billDocRow']|//div[@id='SFAAnalysisSection']/div/div[@class='billDocRow']"
        ):
            name = row.xpath(".//div[@class='text']/span/strong/text()")[0]
            if row.xpath(".//div[@class='pdf']/a/@href"):
                bill.add_document_link(
                    name,
                    row.xpath(".//div[@class='pdf']/a/@href")[0],
                    media_type="application/pdf",
                    on_duplicate="ignore",
                )
            if row.xpath(".//div[@class='html']/a/@href"):
                bill.add_document_link(
                    name,
                    row.xpath(".//div[@class='html']/a/@href")[0],
                    media_type="text/html",
                    on_duplicate="ignore",
                )

    #         # check if action mentions a sub
    #         submatch = re.search(
    #             r"WITH SUBSTITUTE\s+([\w\-\d]+)", action, re.IGNORECASE
    #         )
    #         if submatch and tds[2].xpath("a"):
    #             version_url = tds[2].xpath("a/@href")[0]
    #             version_name = tds[2].xpath("a/text()")[0].strip()
    #             version_name = "Substitute {}".format(version_name)
    #             self.info("Found Substitute {}".format(version_url))
    #             if version_url.lower().endswith(".pdf"):
    #                 mimetype = "application/pdf"
    #             elif version_url.lower().endswith(".htm"):
    #                 mimetype = "text/html"
    #             bill.add_version_link(version_name, version_url, media_type=mimetype)
