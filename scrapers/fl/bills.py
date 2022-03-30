import re
import logging
import datetime
from urllib.parse import urlencode
from collections import defaultdict
from openstates.scrape import Bill, VoteEvent, Scraper
from openstates.utils import format_datetime
from spatula import HtmlPage, HtmlListPage, XPath, SelectorError, PdfPage, URL

# from https://stackoverflow.com/questions/38015537/python-requests-exceptions-sslerror-dh-key-too-small
import requests

requests.packages.urllib3.disable_warnings()
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ":HIGH:!DH:!aNULL"


class PaginationError(Exception):
    pass


class SubjectPDF(PdfPage):
    preserve_layout = False

    def get_source_from_input(self):
        return f"http://www.leg.state.fl.us/data/session/{self.input['session']}/citator/Daily/subindex.pdf"

    def process_page(self):
        """
        sort of a state machine

        after a blank line if there's an all caps phrase that's the new subject

        if a line contains (H|S)(\\d+) that bill gets current subject
        """
        subjects = defaultdict(set)

        SUBJ_RE = re.compile("^[A-Z ,()]+$")
        BILL_RE = re.compile(r"[HS]\d+(?:-[A-Z])?")

        subject = None

        for line in self.text.splitlines():
            if SUBJ_RE.match(line):
                subject = line.lower().strip()
            elif subject and BILL_RE.findall(line):
                for bill in BILL_RE.findall(line):
                    # normalize bill id to [SH]#
                    bill = bill.replace("-", "")
                    subjects[bill].add(subject)

        return subjects


class BillList(HtmlListPage):
    selector = XPath("//a[contains(@href, '/Session/Bill/')]")
    next_page_selector = XPath("//a[@class='next']/@href")
    dependencies = {"subjects": SubjectPDF}

    def get_source_from_input(self):
        # to test scrape an individual bill, add &billNumber=1351
        return URL(
            f"https://flsenate.gov/Session/Bills/{self.input['session']}?chamber=both",
            verify=False,
        )

    def get_next_source(self):
        # eliminate duplicates, not uncommon to have multiple "Next->" links
        try:
            next_urls = self.next_page_selector.match(self.root)
        except SelectorError:
            return

        # TODO: automatically reduce <a> elements to hrefs?

        # non-unique options
        if len(set(next_urls)) > 1:
            raise PaginationError("get_next_page returned multiple links: {next_urls}")

        return next_urls[0]

    def process_item(self, item):
        bill_id = item.text.strip()
        title = item.xpath("string(../following-sibling::td[1])").strip()
        sponsor = item.xpath("string(../following-sibling::td[2])").strip()
        bill_url = item.attrib["href"] + "/ByCategory"

        if bill_id.startswith(("SB ", "HB ", "SPB ", "HPB ")):
            bill_type = "bill"
        elif bill_id.startswith(("HR ", "SR ")):
            bill_type = "resolution"
        elif bill_id.startswith(("HJR ", "SJR ")):
            bill_type = "joint resolution"
        elif bill_id.startswith(("SCR ", "HCR ")):
            bill_type = "concurrent resolution"
        elif bill_id.startswith(("SM ", "HM ")):
            bill_type = "memorial"
        else:
            raise ValueError("Failed to identify bill type.")

        bill = Bill(
            bill_id,
            self.input["session"],
            title,
            chamber="lower" if bill_id[0] == "H" else "upper",
            classification=bill_type,
        )
        bill.add_source(bill_url)

        # normalize id from HB 0004 to H4
        subj_bill_id = re.sub(r"(H|S)\w+ 0*(\d+)", r"\1\2", bill_id)
        bill.subject = list(self.subjects[subj_bill_id])

        sponsor = re.sub(r"^(?:Rep|Sen)\.\s", "", sponsor)
        sponsor = re.sub(r",\s+(Jr|Sr)\.", r" \1.", sponsor)
        for sp in sponsor.split(", "):
            sp = sp.strip()
            sp_type = "organization" if "committee" in sp.lower() else "person"
            bill.add_sponsorship(sp, "primary", sp_type, True)

        return BillDetail(bill)


class BillDetail(HtmlPage):
    input_type = Bill
    example_input = Bill(
        "HB 1", "2021", "title", chamber="upper", classification="bill"
    )
    example_source = "https://flsenate.gov/Session/Bill/2021/1"

    def get_source_from_input(self):
        return self.input.sources[0]["url"]

    def process_page(self):
        if self.root.xpath("//div[@id = 'tabBodyBillHistory']//table"):
            self.process_history()
            self.process_versions()
            self.process_analysis()
            self.process_amendments()
            self.process_summary()
        yield self.input  # the bill, now augmented
        yield HouseSearchPage(self.input)
        yield from self.process_votes()

    def process_summary(self):
        summary = self.root.xpath(
            'string(//div[@id="main"]/div/div/p[contains(@class,"width80")])'
        ).strip()
        # The site indents the CLAIM and amount lines when present
        summary = summary.replace("            ", "")
        if summary != "":
            self.input.add_abstract(summary, note="summary")

    def process_versions(self):
        try:
            version_table = self.root.xpath("//div[@id = 'tabBodyBillText']/table")[0]
            for tr in version_table.xpath("tbody/tr"):
                name = tr.xpath("string(td[1])").strip()
                version_url = tr.xpath("td/a[1]")[0].attrib["href"]
                if version_url.endswith("PDF"):
                    mimetype = "application/pdf"
                elif version_url.endswith("HTML"):
                    mimetype = "text/html"

                self.input.add_version_link(
                    name, version_url, media_type=mimetype, on_duplicate="ignore"
                )
        except IndexError:
            self.input.extras["places"] = []  # set places to something no matter what
            self.logger.warning("No version table for {}".format(self.input.identifier))

    # 2020 SB 230 is a Bill with populated amendments:
    # http://flsenate.gov/Session/Bill/2020/230/?Tab=Amendments
    def process_amendments(self):
        commmittee_amend_table = self.root.xpath(
            "//div[@id = 'tabBodyAmendments']" "//div[@id='CommitteeAmendment']//table"
        )
        if commmittee_amend_table:
            self.process_amendments_table(commmittee_amend_table, "Committee")

        floor_amend_table = self.root.xpath(
            "//div[@id = 'tabBodyAmendments']" "//div[@id='FloorAmendment']//table"
        )
        if floor_amend_table:
            self.process_amendments_table(floor_amend_table, "Floor")

    def process_amendments_table(self, table, amend_type):
        urls = set()
        try:
            version_to_amend = table[0].xpath("string(caption)").strip()
            for tr in table[0].xpath("tbody/tr"):
                name = tr.xpath("string(td[1])").strip().split("\n")[0].strip()

                # Amendment titles don't show which version they're amending, so add that
                name = "{} to {}".format(name, version_to_amend)

                for link in tr.xpath("td[5]/a"):
                    version_url = link.attrib["href"]

                    # avoid duplicates
                    if version_url in urls:
                        continue
                    urls.add(version_url)

                    if version_url.endswith("PDF"):
                        mimetype = "application/pdf"

                    elif version_url.endswith("HTML"):
                        mimetype = "text/html"

                    self.input.add_document_link(
                        name, version_url, media_type=mimetype, on_duplicate="ignore"
                    )
        except IndexError:
            self.logger.warning(
                "No {} amendments table for {}".format(
                    amend_type, self.input.identifier
                )
            )

    def process_analysis(self):
        try:
            analysis_table = self.root.xpath("//div[@id = 'tabBodyAnalyses']/table")[0]
            for tr in analysis_table.xpath("tbody/tr"):
                name = tr.xpath("string(td[1])").strip()
                name += " -- " + tr.xpath("string(td[3])").strip()
                name = re.sub(r"\s+", " ", name)
                date = tr.xpath("string(td[4])").strip()
                if date:
                    name += " (%s)" % date
                analysis_url = tr.xpath("td/a")[0].attrib["href"]
                self.input.add_document_link(name, analysis_url, on_duplicate="ignore")
        except IndexError:
            self.logger.warning(
                "No analysis table for {}".format(self.input.identifier)
            )

    def process_history(self):
        hist_table = self.root.xpath("//div[@id = 'tabBodyBillHistory']//table")[0]

        for tr in hist_table.xpath("tbody/tr"):
            date = tr.xpath("string(td[1])")
            date = datetime.datetime.strptime(date, "%m/%d/%Y").date().isoformat()

            actor = tr.xpath("string(td[2])")
            if not actor:
                actor = None
            chamber = {"Senate": "upper", "House": "lower"}.get(actor, None)
            if chamber:
                actor = None

            act_text = tr.xpath("string(td[3])").strip()
            for action in act_text.split("\u2022"):
                action = action.strip()
                if not action:
                    continue

                action = re.sub(r"-(H|S)J\s+(\d+)$", "", action)

                atype = []
                if action.startswith("Referred to"):
                    atype.append("referral-committee")
                elif action.startswith("Favorable by"):
                    atype.append("committee-passage-favorable")
                elif action == "Filed":
                    atype.append("filing")
                elif action.startswith("Withdrawn"):
                    atype.append("withdrawal")
                elif action.startswith("Died"):
                    atype.append("failure")
                elif action.startswith("Introduced"):
                    atype.append("introduction")
                elif action.startswith("Read 2nd time"):
                    atype.append("reading-2")
                elif action.startswith("Read 3rd time"):
                    atype.append("reading-3")
                elif action.startswith("Passed;"):
                    atype.append("passage")
                elif action.startswith("Passed as amended"):
                    atype.append("passage")
                elif action.startswith("Adopted"):
                    atype.append("passage")
                elif action.startswith("CS passed"):
                    atype.append("passage")
                elif action == "Approved by Governor":
                    atype.append("executive-signature")
                elif action == "Vetoed by Governor":
                    atype.append("executive-veto")

                self.input.add_action(
                    action,
                    date,
                    organization=actor,
                    chamber=chamber,
                    classification=atype,
                )

    def process_votes(self):
        vote_tables = self.root.xpath("//div[@id='tabBodyVoteHistory']//table")

        for vote_table in vote_tables:
            for tr in vote_table.xpath("tbody/tr"):
                vote_date = tr.xpath("string(td[3])").strip()
                if vote_date.isalpha():
                    vote_date = tr.xpath("string(td[2])").strip()
                try:
                    vote_date = datetime.datetime.strptime(
                        vote_date, "%m/%d/%Y %H:%M %p"
                    )
                except ValueError:
                    self.logger.logger.warning("bad vote date: {}".format(vote_date))

                vote_date = format_datetime(vote_date, "US/Eastern")

                vote_url = tr.xpath("td[4]/a")[0].attrib["href"]
                if "SenateVote" in vote_url:
                    yield FloorVote(
                        dict(date=vote_date, chamber="upper", bill=self.input),
                        source=vote_url,
                    )
                elif "HouseVote" in vote_url:
                    yield FloorVote(
                        dict(
                            date=vote_date,
                            chamber="lower",
                            bill=self.input,
                        ),
                        source=vote_url,
                    )
                else:
                    yield UpperComVote(
                        dict(date=vote_date, bill=self.input),
                        source=vote_url,
                    )
        else:
            self.logger.warning("No vote table for {}".format(self.input.identifier))


class FloorVote(PdfPage):
    preserve_layout = True

    def process_page(self):
        MOTION_INDEX = 4
        TOTALS_INDEX = 6
        VOTE_START_INDEX = 9

        lines = self.text.splitlines()

        if len(lines) < 2:
            self.logger.warning("Bad PDF! " + self.source.url)
            return

        motion = lines[MOTION_INDEX].strip()
        # Sometimes there is no motion name, only "Passage" in the line above
        if not motion and not lines[MOTION_INDEX - 1].startswith("Calendar Page:"):
            motion = lines[MOTION_INDEX - 1]
            MOTION_INDEX -= 1
            TOTALS_INDEX -= 1
            VOTE_START_INDEX -= 1
        else:
            assert motion, "Floor vote's motion name appears to be empty"

        for _extra_motion_line in range(2):
            MOTION_INDEX += 1
            if lines[MOTION_INDEX].strip():
                motion = "{}, {}".format(motion, lines[MOTION_INDEX].strip())
                TOTALS_INDEX += 1
                VOTE_START_INDEX += 1
            else:
                break

        (yes_count, no_count, nv_count) = [
            int(x)
            for x in re.search(
                r"^\s+Yeas - (\d+)\s+Nays - (\d+)\s+Not Voting - (\d+)\s*$",
                lines[TOTALS_INDEX],
            ).groups()
        ]
        result = "pass" if yes_count > no_count else "fail"

        vote = VoteEvent(
            start_date=self.input["date"],
            chamber=self.input["chamber"],
            bill=self.input["bill"],
            motion_text=motion,
            result=result,
            classification="passage",
        )
        vote.add_source(self.source.url)
        vote.set_count("yes", yes_count)
        vote.set_count("no", no_count)
        vote.set_count("not voting", nv_count)

        for line in lines[VOTE_START_INDEX:]:
            if not line.strip():
                break

            if " President " in line:
                line = line.replace(" President ", " ")
            elif " Speaker " in line:
                line = line.replace(" Speaker ", " ")

            # Votes follow the pattern of:
            # [vote code] [member name]-[district number]
            for vtype, member in re.findall(r"\s*(Y|N|EX|AV)\s+(.*?)-\d{1,3}\s*", line):
                vtype = {"Y": "yes", "N": "no", "EX": "excused", "AV": "abstain"}[vtype]
                member = member.strip()
                vote.vote(vtype, member)

        # check totals line up
        yes_count = no_count = nv_count = 0
        for vc in vote.counts:
            if vc["option"] == "yes":
                yes_count = vc["value"]
            elif vc["option"] == "no":
                no_count = vc["value"]
            else:
                nv_count += vc["value"]

        for vr in vote.votes:
            if vr["option"] == "yes":
                yes_count -= 1
            elif vr["option"] == "no":
                no_count -= 1
            else:
                nv_count -= 1

        if yes_count != 0 or no_count != 0:
            raise ValueError("vote count incorrect: " + self.url)

        if nv_count != 0:
            # On a rare occasion, a member won't have a vote code,
            # which indicates that they didn't vote. The totals reflect
            # this.
            self.logger.info("Votes don't add up; looking for additional ones")
            for line in lines[VOTE_START_INDEX:]:
                if not line.strip():
                    break
                for member in re.findall(r"\s{8,}([A-Z][a-z\'].*?)-\d{1,3}", line):
                    member = member.strip()
                    vote.vote("not voting", member)
        yield vote


class UpperComVote(PdfPage):
    preserve_layout = True

    def process_page(self):
        lines = self.text.splitlines()
        (_, motion) = lines[5].split("FINAL ACTION:")
        motion = motion.strip()
        if not motion:
            self.logger.warning("Vote appears to be empty")
            return

        vote_top_row = [
            lines.index(x)
            for x in lines
            if re.search(r"^\s+Yea\s+Nay.*?(?:\s+Yea\s+Nay)+$", x)
        ][0]
        yea_columns_end = lines[vote_top_row].index("Yea") + len("Yea")
        nay_columns_begin = lines[vote_top_row].index("Nay")

        votes = {"yes": [], "no": [], "other": []}
        for line in lines[(vote_top_row + 1) :]:
            if line.strip():
                member = re.search(
                    r"""(?x)
                        ^\s+(?:[A-Z\-]+)?\s+    # Possible vote indicator
                        ([A-Z][a-z]+            # Name must have lower-case characters
                        [\w\-\s]+)              # Continue looking for the rest of the name
                        (?:,[A-Z\s]+?)?         # Leadership has an all-caps title
                        (?:\s{2,}.*)?           # Name ends when many spaces are seen
                        """,
                    line,
                ).group(1)
                # sometimes members have trailing X's from other motions in the
                # vote sheet we aren't collecting
                member = re.sub(r"(\s+X)+", "", member)
                # Usually non-voting members won't even have a code listed
                # Only a couple of codes indicate an actual vote:
                # "VA" (vote after roll call) and "VC" (vote change)
                did_vote = bool(re.search(r"^\s+(X|VA|VC)\s+[A-Z][a-z]", line))
                if did_vote:
                    # Check where the "X" or vote code is on the page
                    vote_column = len(line) - len(line.lstrip())
                    if vote_column <= yea_columns_end:
                        votes["yes"].append(member)
                    elif vote_column >= nay_columns_begin:
                        votes["no"].append(member)
                    else:
                        raise ValueError(
                            "Unparseable vote found for {} in {}:\n{}".format(
                                member, self.source.url, line
                            )
                        )
                else:
                    votes["other"].append(member)

            # End loop as soon as no more members are found
            else:
                break

        totals = re.search(r"(?msu)\s+(\d{1,3})\s+(\d{1,3})\s+.*?TOTALS", self.text)
        if not totals:
            self.logger.warning(f"Missing totals for {self.source.url}, skipping")
            return

        totals = totals.groups()
        yes_count = int(totals[0])
        no_count = int(totals[1])
        result = "pass" if (yes_count > no_count) else "fail"

        vote = VoteEvent(
            start_date=self.input["date"],
            bill=self.input["bill"],
            chamber="upper",
            motion_text=motion,
            classification="committee-passage",
            result=result,
        )
        vote.add_source(self.source.url)
        vote.set_count("yes", yes_count)
        vote.set_count("no", no_count)
        vote.set_count("other", len(votes["other"]))

        # set voters
        for vtype, voters in votes.items():
            for voter in voters:
                voter = voter.strip()
                # Removes the few voter names with a ton of extra spaces with  VA at the end.
                # Ex: Cruz                                                               VA
                if "  VA" in voter:
                    voter = " ".join(voter.split()[:-2])
                if len(voter) > 0:
                    vote.vote(vtype, voter)

        yield vote


class HouseSearchPage(HtmlListPage):
    """
    House committee roll calls are not available on the Senate's
    website. Furthermore, the House uses an internal ID system in
    its URLs, making accessing those pages non-trivial.

    This will fetch all the House committee votes for the
    given bill, and add the votes to that object.
    """

    input_type = Bill
    example_input = Bill(
        "HB 1", "2020", "title", chamber="upper", classification="bill"
    )
    selector = XPath('//a[contains(@href, "/Bills/billsdetail.aspx?BillId=")]/@href')

    def get_source_from_input(self):
        url = "https://www.myfloridahouse.gov/Sections/Bills/bills.aspx"
        # Keep the digits and all following characters in the bill's ID
        bill_number = re.search(r"^\w+\s(\d+\w*)$", self.input.identifier).group(1)
        session_number = {
            "2022C": "95",
            "2022": "93",
            "2021B": "94",
            "2021A": "92",
            "2021": "90",
            "2020": "89",
            "2019": "87",
            "2018": "86",
            "2017A": "85",
            "2017": "83",
            "2016": "80",
            "2015C": "82",
            "2015B": "81",
            "2015A": "79",
            "2015": "76",
            "2014O": "78",
            "2014A": "77",
            "2016O": "84",
        }[self.input.legislative_session]

        form = {"Chamber": "B", "SessionId": session_number, "BillNumber": bill_number}
        return url + "?" + urlencode(form)

    def process_item(self, item):
        return HouseBillPage(self.input, source=item)


class HouseBillPage(HtmlListPage):
    selector = XPath('//a[text()="See Votes"]/@href', min_items=0)
    example_input = Bill(
        "HB 1", "2020", "title", chamber="upper", classification="bill"
    )
    example_source = (
        "https://www.myfloridahouse.gov/Sections/Bills/billsdetail.aspx?BillId=69746"
    )

    def process_item(self, item):
        return HouseComVote(self.input, source=item)


class HouseComVote(HtmlPage):
    example_input = Bill(
        "HB 1", "2020", "title", chamber="upper", classification="bill"
    )
    example_source = (
        "https://www.myfloridahouse.gov/Sections/Committees/billvote.aspx?"
        "VoteId=54381&IsPCB=0&BillId=69746"
    )

    def process_page(self):
        # Checks to see if any vote totals are provided
        if (
            len(
                self.root.xpath(
                    '//span[contains(@id, "ctl00_MainContent_lblTotal")]/text()'
                )
            )
            > 0
        ):
            (date,) = self.root.xpath('//span[contains(@id, "lblDate")]/text()')
            date = format_datetime(
                datetime.datetime.strptime(date, "%m/%d/%Y %I:%M:%S %p"), "US/Eastern"
            )
            # ctl00_MainContent_lblTotal //span[contains(@id, "ctl00_MainContent_lblTotal")]
            yes_count = int(
                self.root.xpath('//span[contains(@id, "lblYeas")]/text()')[0]
            )
            no_count = int(
                self.root.xpath('//span[contains(@id, "lblNays")]/text()')[0]
            )
            other_count = int(
                self.root.xpath('//span[contains(@id, "lblMissed")]/text()')[0]
            )
            result = "pass" if yes_count > no_count else "fail"

            (committee,) = self.root.xpath(
                '//span[contains(@id, "lblCommittee")]/text()'
            )
            (action,) = self.root.xpath('//span[contains(@id, "lblAction")]/text()')
            motion = "{} ({})".format(action, committee)

            vote = VoteEvent(
                start_date=date,
                bill=self.input,
                chamber="lower",
                motion_text=motion,
                result=result,
                classification="committee-passage",
            )
            vote.add_source(self.source.url)
            vote.set_count("yes", yes_count)
            vote.set_count("no", no_count)
            vote.set_count("not voting", other_count)

            for member_vote in self.root.xpath(
                '//ul[contains(@class, "vote-list")]/li'
            ):
                if not member_vote.text_content().strip():
                    continue

                (member,) = member_vote.xpath("span[2]//text()")
                (member_vote,) = member_vote.xpath("span[1]//text()")

                member = member.strip()
                if member_vote == "Y":
                    vote.yes(member)
                elif member_vote == "N":
                    vote.no(member)
                elif member_vote == "-":
                    vote.vote("not voting", member)
                # Parenthetical votes appear to not be counted in the
                # totals for Yea, Nay, _or_ Missed
                elif re.search(r"\([YN]\)", member_vote):
                    continue
                else:
                    raise ValueError("Unknown vote type found: {}".format(member_vote))

            return vote


class FlBillScraper(Scraper):
    def scrape(self, session=None):
        self.raise_errors = False
        self.retry_attempts = 1
        self.retry_wait_seconds = 3

        # spatula's logging is better than scrapelib's
        logging.getLogger("scrapelib").setLevel(logging.WARNING)
        bill_list = BillList({"session": session})
        yield from bill_list.do_scrape()
