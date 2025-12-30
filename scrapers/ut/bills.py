import re
import datetime
from dateutil import parser

from openstates.scrape import Scraper, Bill, VoteEvent as Vote
from .actions import Categorizer
from utils import LXMLMixin

import json
import lxml.html
from lxml.etree import ParserError
import pytz
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

SPECIAL_SLUGS = {"2021S1H": "2021Y1", "2021S1S": "2021X1"}

SPONSOR_HOUSE_TO_CHAMBER = {
    "H": "lower",
    "S": "upper",
}


class UTBillScraper(Scraper, LXMLMixin):
    categorizer = Categorizer()
    _TZ = pytz.timezone("America/Denver")

    def scrape(self, session=None, chamber=None):
        if session in SPECIAL_SLUGS:
            session_slug = SPECIAL_SLUGS[session]
        elif "S" in session:
            session_slug = session
        else:
            session_slug = "{}GS".format(session)

        # if you need to test on an individual bill...
        # yield from self.scrape_bill(
        #             'lower',
        #             '2019',
        #             'https://le.utah.gov/~2025/bills/static/SR0002.html',
        #             session_slug,
        #         )

        session_url = "https://le.utah.gov/billlist.jsp?session={}".format(session_slug)

        # For some sessions the link doesn't go straight to the bill list
        doc = self.lxmlize(session_url)

        # Get all of the show/hide bill list elements
        # in order to get the IDs of the actual bill lists
        bill_list_ids = []
        show_hide_elems = doc.cssselect("a.mitem")
        js_id_getter = re.compile(r"javascript:toggleObj\('([^']+)'\)")
        for elem in show_hide_elems:
            list_id_match = js_id_getter.match(elem.get("href"))
            if list_id_match:
                bill_list_ids.append(list_id_match.group(1))
            else:
                self.logger.error(
                    "Failed to find bill list ID out of JS show/hide elem"
                )

        # Capture the bills from each of the bill lists
        for list_id in bill_list_ids:
            bill_link_containers = doc.cssselect(f"#{list_id}")
            for container in bill_link_containers:
                for bill_link in container.cssselect("a"):
                    if bill_link.text.startswith("H"):
                        chamber = "lower"
                    elif bill_link.text.startswith("S"):
                        chamber = "upper"
                    else:
                        raise AssertionError(
                            "Unknown bill type found: {}".format(bill_link.text)
                        )

                    yield from self.scrape_bill(
                        chamber=chamber,
                        session=session,
                        url=bill_link.get("href"),
                        session_slug=session_slug,
                    )

    def scrape_bill(self, chamber, session, url, session_slug):
        page = self.lxmlize(url)

        bill_id = page.cssselect("#breadcrumb li")[-1].text

        (header,) = page.xpath(
            '//h3[@class="heading"]/text() | //h1[@class="heading"]/text()'
        )
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
        bill_id = re.sub(r"\s+", " ", bill_id).strip().replace(".", "")

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=title,
            classification=bill_type,
        )
        bill.add_source(url)

        primary_info = page.xpath('//div[@id="billsponsordiv"]')
        if len(primary_info) == 0:
            # starting 2025 seems UT is rendering bill data from an API/JSON
            # but prior years seem to have static-ish HTML
            # so we have two logic branches here
            # TODO vote processing - need to see what data looks like
            self.scrape_bill_details_from_api(bill, url, session_slug)
        else:
            yield from self.parse_bill_details_from_html(
                bill, bill_id, chamber, page, primary_info
            )

        yield bill

    def parse_bill_details_from_html(self, bill, bill_id, chamber, page, primary_info):
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
            self.warning("Unexpected floor sponsor HTML found")
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
                version.xpath("text()")[0].strip(),
                url,
                media_type="application/pdf",
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

    def scrape_bill_details_from_api(self, bill: Bill, bill_url, session_slug: str):
        # get bill "filename" from bill_url
        bill_filename = bill_url.split("/")[-1].split(".")[0]
        # use datetime to generate a unix epoch timestamp representing now
        # UT seems to do this in milliseconds
        now = int(datetime.datetime.now().timestamp() * 1000)
        api_url = (
            f"https://le.utah.gov/data/{session_slug}/{bill_filename}.json?_={now}"
        )
        response = self.get(api_url)
        data = json.loads(response.content)

        # Sponsorships
        if "primeSponsorName" in data and data["primeSponsorName"]:
            sponsor_name = data["primeSponsorName"]
            sponsor_name = sponsor_name.replace("Sen. ", "").replace("Rep. ", "")
            sponsor_chamber = SPONSOR_HOUSE_TO_CHAMBER[data["primeSponsorHouse"]]
            bill.add_sponsorship(
                sponsor_name,
                classification="primary",
                entity_type="person",
                primary=True,
                chamber=sponsor_chamber,
            )
        if "floorSponsor" in data and data["floorSponsor"]:
            floor_sponsor_name = data["floorSponsorName"]
            floor_sponsor_name = floor_sponsor_name.replace("Sen. ", "").replace(
                "Rep. ", ""
            )
            floor_sponsor_chamber = SPONSOR_HOUSE_TO_CHAMBER[data["floorSponsorHouse"]]
            bill.add_sponsorship(
                floor_sponsor_name,
                classification="cosponsor",
                entity_type="person",
                primary=False,
                chamber=floor_sponsor_chamber,
            )

        # Versions, subjects, code citations
        subjects = set()
        if "billVersionList" in data:

            for version_data in data["billVersionList"]:
                # subjects associated with each version, so dedupe
                for subject_data in version_data["subjectList"]:
                    subjects.add(subject_data["description"])

                for citation in version_data.get("sectionAffectedList", []):
                    bill.add_citation("Utah Code", citation["secNo"], "proposed")

                for doc_data in version_data["billDocs"]:
                    # Some documents in here are not really bill versions, more supplemental documents
                    doc_type = "version"
                    if (
                        doc_data["shortDesc"] == "Fiscal Note"
                        or "Transmittal Letter" in doc_data["shortDesc"]
                        or "Committee Report" in doc_data["shortDesc"]
                    ):
                        doc_type = "document"

                    # There seem to be XML and PDF files on Utah server
                    # the UT bill details page seems to have code to
                    # display the XML as HTML inline

                    if not doc_data["url"].startswith("http"):
                        doc_url = f"https://le.utah.gov{doc_data['url']}"
                    else:
                        doc_url = doc_data["url"]

                    if doc_type == "version":
                        if doc_url.endswith("html") or doc_url.endswith("xml"):
                            bill.add_version_link(
                                doc_data["shortDesc"],
                                doc_url,
                                media_type="text/xml",
                            )

                        pdf_filepath = doc_url.replace(".xml", ".pdf")
                        bill.add_version_link(
                            doc_data["shortDesc"],
                            pdf_filepath,
                            media_type="application/pdf",
                        )
                    else:
                        if doc_url.endswith("html") or doc_url.endswith("xml"):
                            bill.add_document_link(
                                doc_data["shortDesc"], doc_url, media_type="text/xml"
                            )
                        elif doc_url.lower().endswith("pdf"):
                            bill.add_document_link(
                                doc_data["shortDesc"],
                                doc_url,
                                media_type="application/pdf",
                            )
                        else:
                            self.warning(
                                f"Encountered unexpected document type for {doc_url}"
                            )

        for subject in subjects:
            bill.add_subject(subject)

        # Actions
        if "actionHistoryList" in data:
            cmte_match_re = re.compile(r"(committee|comm|to rules)", re.IGNORECASE)
            for action_data in data["actionHistoryList"]:
                categorizer_result = self.categorizer.categorize(
                    action_data["description"]
                )
                actor = "legislature"
                if action_data["owner"] == "Legislative Research and General Counsel":
                    actor = "legislature"
                elif "governor" in action_data["owner"].lower():
                    actor = "executive"
                elif "clerk of the house" in action_data["owner"].lower():
                    actor = "lower"
                elif "clerk of the senate" in action_data["owner"].lower():
                    actor = "upper"
                elif action_data["owner"].startswith("Senate"):
                    actor = "upper"
                elif action_data["owner"].startswith("House"):
                    actor = "lower"
                # we can also fall back in a few ways
                # one is to use action description which often starts with House or Senate
                elif action_data["description"].startswith("Senate"):
                    actor = "upper"
                elif action_data["description"].startswith("House"):
                    actor = "lower"
                else:
                    self.warning(
                        f"Found unexpected actor {action_data['owner']} at {api_url}"
                    )

                if ":" in action_data["actionDate"]:
                    date = parser.parse(action_data["actionDate"])
                    date = self._TZ.localize(date)
                else:
                    date = datetime.datetime.strptime(
                        action_data["actionDate"], "%m/%d/%Y"
                    ).date()
                    date = date.strftime("%Y-%m-%d")

                # In cases where action is a committee referral, include "owner" in description
                # because the "owner" data point contains the committee name
                # this provides important context to the action
                committee = None
                action_owner = action_data["owner"]
                if re.search(cmte_match_re, action_data["description"]):
                    description = f"{action_data['description']} [{action_owner}]"
                    match = re.search(
                        r"(?:Senate|House) (.+) (?:\bCommittee)",
                        action_owner,
                        flags=re.IGNORECASE,
                    )
                    if match:
                        committee = match.group(1).strip()
                else:
                    description = action_data["description"]

                action_instance = bill.add_action(
                    date=date,
                    description=description,
                    classification=categorizer_result["classification"],
                    chamber=actor,
                )

                if committee:
                    action_instance.add_related_entity(
                        committee, entity_type="organization"
                    )

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

            elif action == "Governor Vetoed":
                actor = "executive"

            elif action == "Governor Line Item Veto":
                actor = "executive"

            elif action == "to standing committee":
                comm = row.xpath("td[3]/font/text()")[0]
                action = "to " + comm

            attrs = self.categorizer.categorize(action)
            typ = attrs["classification"]

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
        try:
            page = lxml.html.fromstring(page)
        except ParserError:
            self.logger.warning(f"Could not parse HTML vote page {url}")

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
