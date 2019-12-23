import re
import datetime

from pupa.scrape import Scraper, Bill, VoteEvent as Vote
from openstates.utils import LXMLMixin

import lxml.html
import scrapelib

SUB_BLACKLIST = [
    "Second Substitute",
    "Third Substitute",
    "Fourth Substitute",
    "Fifth Substitute",
    "Sixth Substitute",
    "Seventh Substitute",
    "Eighth Substitute",
    "Ninth Substitute",
    "Substitute",
]  # Pages are the same, we'll strip this from bills we catch.


class UTBillScraper(Scraper, LXMLMixin):
    def scrape(self, session=None, chamber=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        # if you need to test on an individual bill...
        # yield from self.scrape_bill(
        #             chamber='lower',
        #             session='2019',
        #             bill_id='H.B. 87',
        #             url='https://le.utah.gov/~2019/bills/static/HB0087.html'
        #         )

        # Identify the index page for the given session
        sessions = self.lxmlize("http://le.utah.gov/Documents/bills.htm")

        session_search_text = session
        if "s" not in session.lower() and "h" not in session.lower():
            session_search_text += "GS"

        sessions = sessions.xpath(
            '//li/a[contains(@href, "{}")]'.format(session_search_text)
        )

        session_url = ""
        S = [
            i
            for i, _ in enumerate(self.jurisdiction.legislative_sessions)
            if _["identifier"] == session
        ][0]
        for elem in sessions:
            if (
                re.sub(r"\s+", " ", elem.xpath("text()")[0])
                == self.jurisdiction.legislative_sessions[S]["_scraped_name"]
            ):
                session_url = elem.xpath("@href")[0]
        assert session_url

        # For some sessions the link doesn't go straight to the bill list
        doc = self.lxmlize(session_url)
        replacement_session_url = doc.xpath(
            '//a[text()="Numbered Bills" and contains'
            '(@href, "DynaBill/BillList")]/@href'
        )
        if replacement_session_url:
            (session_url,) = replacement_session_url

        # Identify all the bill lists linked from a given session's page
        bill_indices = [
            re.sub(r"^r", "", x)
            for x in self.lxmlize(session_url).xpath('//div[contains(@id, "0")]/@id')
        ]

        # Capture the bills from each of the bill lists
        for bill_index in bill_indices:
            if bill_index.startswith("H"):
                chamber = "lower"
            elif bill_index.startswith("S"):
                chamber = "upper"
            else:
                raise AssertionError("Unknown bill type found: {}".format(bill_index))

            bill_index = self.lxmlize(session_url + "&bills=" + bill_index)
            bills = bill_index.xpath('//a[contains(@href, "/bills/static/")]')

            for bill in bills:
                yield from self.scrape_bill(
                    chamber=chamber,
                    session=session,
                    bill_id=bill.xpath("text()")[0],
                    url=bill.xpath("@href")[0],
                )

    def scrape_bill(self, chamber, session, bill_id, url):
        page = self.lxmlize(url)

        (header,) = page.xpath('//h3[@class="heading"]/text()')
        title = header.replace(bill_id, "").strip()

        if ".B. " in bill_id:
            bill_type = "bill"
        elif bill_id.startswith("H.R. ") or bill_id.startswith("S.R. "):
            bill_type = "resolution"
        elif ".C.R. " in bill_id:
            bill_type = "concurrent resolution"
        elif ".J.R. " in bill_id:
            bill_type = "joint resolution"

        for flag in SUB_BLACKLIST:
            if flag in bill_id:
                bill_id = bill_id.replace(flag, " ")
        bill_id = re.sub(r"\s+", " ", bill_id).strip()

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=title,
            classification=bill_type,
        )
        bill.add_source(url)

        primary_info = page.xpath('//div[@id="billsponsordiv"]')
        for info in primary_info:
            try:
                (title, name) = [
                    x.strip() for x in info.xpath(".//text()") if x.strip()
                ]
            except ValueError:
                self.warning("Could not find sponsor's name for {}".format(bill_id))
                continue
            assert title == "Bill Sponsor:"
            name = name.replace("Sen. ", "").replace("Rep. ", "")
            bill.add_sponsorship(
                name, classification="primary", entity_type="person", primary=True
            )
        floor_info = page.xpath('//div[@id="floorsponsordiv"]//text()')
        floor_info = [x.strip() for x in floor_info if x.strip()]
        if len(floor_info) in (0, 1):
            # This indicates that no floor sponsor was found
            pass
        elif len(floor_info) == 2:
            assert floor_info[0] == "Floor Sponsor:"
            floor_sponsor = floor_info[1].replace("Sen. ", "").replace("Rep. ", "")
            bill.add_sponsorship(
                floor_sponsor,
                classification="cosponsor",
                entity_type="person",
                primary=False,
            )
        else:
            raise AssertionError("Unexpected floor sponsor HTML found")

        versions = page.xpath(
            '//b[text()="Bill Text"]/following-sibling::ul/li/'
            'a[text() and not(text()=" ")]'
        )

        for version in versions:

            # sometimes the href is on the following <a> tag and the tag we
            # have has an onclick
            url = version.get("href")
            if not url:
                url = version.xpath("following-sibling::a[1]/@href")[0]

            bill.add_version_link(
                version.xpath("text()")[0].strip(), url, media_type="application/pdf"
            )

        for related in page.xpath(
            '//b[text()="Related Documents "]/following-sibling::ul/li/'
            'a[contains(@class,"nlink")]'
        ):
            href = related.xpath("@href")[0]
            if ".fn.pdf" in href:
                bill.add_document_link(
                    "Fiscal Note", href, media_type="application/pdf"
                )
            else:
                text = related.xpath("text()")[0]
                bill.add_document_link(text, href, media_type="application/pdf")

        subjects = []
        for link in page.xpath("//a[contains(@href, 'RelatedBill')]"):
            subjects.append(link.text.strip())
        bill.subject = subjects

        if page.xpath('//div[@id="billStatus"]//table'):
            status_table = page.xpath('//div[@id="billStatus"]//table')[0]
            yield from self.parse_status(bill, status_table, chamber)

        yield bill

    def parse_status(self, bill, status_table, chamber):
        page = status_table
        uniqid = 0

        for row in page.xpath("tr")[1:]:
            uniqid += 1
            date = row.xpath("string(td[1])")
            date = date.split("(")[0]
            date = datetime.datetime.strptime(date.strip(), "%m/%d/%Y").date()
            date = date.strftime("%Y-%m-%d")
            action = row.xpath("string(td[2])").strip()
            actor = chamber

            if "/ " in action:
                actor = action.split("/ ")[0].strip()

                if actor == "House":
                    actor = "lower"
                elif actor == "Senate":
                    actor = "upper"
                elif actor == "LFA":
                    actor = "legislature"  # 'Office of the Legislative Fiscal Analyst'
                else:
                    raise Exception(actor)

                action = "/".join(action.split("/ ")[1:]).strip()

            if action == "Governor Signed":
                actor = "executive"
                typ = "executive-signature"
            elif action == "Governor Vetoed":
                actor = "executive"
                typ = "executive-veto"
            elif action == "Governor Line Item Veto":
                actor = "executive"
                typ = "executive-veto-line-item"
            elif action.startswith("1st reading"):
                typ = ["introduction", "reading-1"]
            elif action == "to Governor":
                typ = "executive-receipt"
            elif action == "passed 3rd reading":
                typ = "passage"
            elif action.startswith("passed 2nd & 3rd readings"):
                typ = "passage"
            elif action == "to standing committee":
                comm = row.xpath("td[3]/font/text()")[0]
                action = "to " + comm
                typ = "referral-committee"
            elif action.startswith("2nd reading"):
                typ = "reading-2"
            elif action.startswith("3rd reading"):
                typ = "reading-3"
            elif action == "failed":
                typ = "failure"
            elif action.startswith("2nd & 3rd readings"):
                typ = ["reading-2", "reading-3"]
            elif action == "passed 2nd reading":
                typ = "reading-2"
            elif "Comm - Favorable Recommendation" in action:
                typ = "committee-passage-favorable"
            elif action == "committee report favorable":
                typ = "committee-passage-favorable"
            else:
                typ = None
            act = bill.add_action(
                description=action, date=date, chamber=actor, classification=typ
            )
            act.extras = {"_vote_id": str(uniqid)}

            # Check if this action is a vote
            vote_links = row.xpath("./td[4]//a")
            for vote_link in vote_links:
                vote_url = vote_link.attrib["href"]
                if not vote_url.endswith("txt"):
                    yield from self.parse_html_vote(
                        bill, actor, date, action, vote_url, uniqid
                    )
                else:
                    yield from self.parse_vote(
                        bill, actor, date, action, vote_url, uniqid
                    )

    def scrape_committee_vote(self, bill, actor, date, motion, page, url, uniqid):
        votes = page.xpath("//table")[0]
        rows = votes.xpath(".//tr")[0]
        if rows[0].text_content() == "Votes:":
            # New webste
            rows = votes.xpath(".//tr")[2]
        yno = rows.xpath(".//td")
        if len(yno) < 3:
            yes = yno[0]
            no, other = None, None
        else:
            yes, _, no, _, other = rows.xpath(".//td")[:5]

        def proc_block(obj, typ):
            if obj is None:
                return {"type": None, "count": None, "votes": []}
            votes = []
            for vote in obj.xpath("./text()"):
                if vote.strip():
                    vote = vote.strip()
                    if vote:
                        votes.append(vote)
            count = len(votes)
            return {"type": typ, "count": count, "votes": votes}

        vote_dict = {
            "yes": proc_block(yes, "yes"),
            "no": proc_block(no, "no"),
            "other": proc_block(other, "other"),
        }

        yes_count = vote_dict["yes"]["count"]
        no_count = vote_dict["no"]["count"] or 0
        other_count = vote_dict["other"]["count"] or 0
        vote = Vote(
            chamber=actor,
            start_date=date,
            motion_text=motion,
            identifier=str(uniqid),
            result="pass" if (yes_count > no_count) else "fail",
            classification="passage",
            bill=bill,
        )
        vote.extras = {"_vote_id": uniqid}
        vote.add_source(url)
        vote.set_count("yes", yes_count)
        vote.set_count("no", no_count)
        vote.set_count("other", other_count)
        for key in vote_dict:
            for voter in vote_dict[key]["votes"]:
                vote.vote(key, voter)

        yield vote

    def parse_html_vote(self, bill, actor, date, motion, url, uniqid):
        try:
            page = self.get(url).text
        except scrapelib.HTTPError:
            self.warning("A vote page not found for bill {}".format(bill.identifier))
            return
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        descr = page.xpath("//b")[0].text_content()
        if descr == "":
            # New page method
            descr = page.xpath("//center")[0].text

        if "on voice vote" in descr:
            return

        if "committee" in descr.lower():
            yield from self.scrape_committee_vote(
                bill, actor, date, motion, page, url, uniqid
            )
            return

        passed = None
        if "Passed" in descr:
            passed = True
        elif "Failed" in descr:
            passed = False
        elif "UTAH STATE LEGISLATURE" in descr:
            return
        elif descr.strip() == "-":
            return
        else:
            self.warning(descr)
            raise NotImplementedError("Can't see if we passed or failed")

        headings = page.xpath("//b")[1:]
        votes = page.xpath("//table")
        sets = zip(headings, votes)
        vdict = {}
        for (typ, votes) in sets:
            txt = typ.text_content()
            arr = [x.strip() for x in txt.split("-", 1)]
            if len(arr) != 2:
                continue
            v_txt, count = arr
            v_txt = v_txt.strip()
            count = int(count)
            people = [
                x.text_content().strip() for x in votes.xpath(".//font[@face='Arial']")
            ]

            vdict[v_txt] = {"count": count, "people": people}

        vote = Vote(
            chamber=actor,
            start_date=date,
            motion_text=motion,
            result="pass" if passed else "fail",
            bill=bill,
            classification="passage",
            identifier=str(uniqid),
        )
        vote.set_count("yes", vdict["Yeas"]["count"])
        vote.set_count("no", vdict["Nays"]["count"])
        vote.set_count("other", vdict["Absent or not voting"]["count"])
        vote.add_source(url)

        for person in vdict["Yeas"]["people"]:
            vote.yes(person)
        for person in vdict["Nays"]["people"]:
            vote.no(person)
        for person in vdict["Absent or not voting"]["people"]:
            vote.vote("other", person)

        yield vote

    def parse_vote(self, bill, actor, date, motion, url, uniqid):
        page = self.get(url).text
        bill.add_source(url)
        vote_re = re.compile(
            r"YEAS -?\s?(\d+)(.*)NAYS -?\s?(\d+)"
            r"(.*)ABSENT( OR NOT VOTING)? -?\s?"
            r"(\d+)(.*)",
            re.MULTILINE | re.DOTALL,
        )
        match = vote_re.search(page)
        yes_count = int(match.group(1))
        no_count = int(match.group(3))
        other_count = int(match.group(6))

        if yes_count > no_count:
            passed = True
        else:
            passed = False

        if actor == "upper" or actor == "lower":
            vote_chamber = actor
        else:
            vote_chamber = ""

        vote = Vote(
            chamber=vote_chamber,
            start_date=date,
            motion_text=motion,
            result="pass" if passed else "fail",
            identifier=str(uniqid),
            classification="passage",
            bill=bill,
        )
        vote.add_source(url)
        vote.set_count("yes", yes_count)
        vote.set_count("no", no_count)
        vote.set_count("other", other_count)

        yes_votes = re.split(r"\s{2,}", match.group(2).strip())
        no_votes = re.split(r"\s{2,}", match.group(4).strip())
        other_votes = re.split(r"\s{2,}", match.group(7).strip())

        for yes in yes_votes:
            if yes:
                vote.yes(yes)
        for no in no_votes:
            if no:
                vote.no(no)
        for other in other_votes:
            if other:
                vote.vote("other", other)

        yield vote
