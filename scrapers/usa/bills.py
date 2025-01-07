import datetime
import lxml
import pytz
import re
import requests
import xml.etree.ElementTree as ET

from openstates.scrape import Bill, Scraper, VoteEvent, Event


# NOTE: This is a US federal bill scraper designed to output bills in the
# openstates format, for compatibility with systems that already ingest the pupa format.

# If you're looking to just collect federal bill data, you're probably better off with
# https://github.com/unitedstates/congress which offers more backdata.


class USBillScraper(Scraper):
    # https://www.govinfo.gov/rss/billstatus-batch.xml
    # https://github.com/usgpo/bill-status/blob/master/BILLSTATUS-XML_User_User-Guide.md

    # good sample bills:
    # https://www.govinfo.gov/bulkdata/BILLSTATUS/116/hr/BILLSTATUS-116hr8337.xml
    # vetoed:
    # https://www.govinfo.gov/bulkdata/BILLSTATUS/116/sjres/BILLSTATUS-116sjres68.xml

    # custom namespace, see
    # https://docs.python.org/2/library/xml.etree.elementtree.html#parsing-xml-with-namespaces
    ns = {"us": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    _TZ = pytz.timezone("US/Eastern")

    chambers = {"House": "lower", "Joint": "joint", "Senate": "upper"}
    chamber_map = {"upper": "s", "lower": "h"}
    chamber_code = {"S": "upper", "H": "lower", "J": "legislature"}
    vote_codes = {
        "Aye": "yes",
        "Yea": "yes",
        "Yes": "yes",
        "Nay": "no",
        "No": "no",
        "Not Voting": "not voting",
        "Present": "other",
        "Present, Giving Live Pair": "other",
    }
    senate_statuses = {
        "Agreed to": "pass",
        "Amendment Agreed to": "pass",
        "Bill Passed": "pass",
        "Confirmed": "pass",
        "Rejected": "fail",
        "Passed": "pass",
        "Nomination Confirmed": "pass",
        "Cloture Motion Agreed to": "pass",
        "Cloture Motion Rejected": "fail",
        "Cloture on the Motion to Proceed Rejected": "fail",
        "Cloture on the Motion to Proceed Agreed to": "pass",
        "Conference Report Agreed to": "pass",
        "Amendment Rejected": "fail",
        "Decision of Chair Sustained": "pass",
        "Motion Agreed to": "pass",
        "Motion for Attendance Agreed to": "pass",
        "Motion to Discharge Agreed to": "pass",
        "Motion to Discharge Rejected": "fail",
        "Motion to Reconsider Agreed to": "pass",
        "Motion to Table Failed": "fail",
        "Motion to Table Agreed to": "pass",
        "Motion to Table Motion to Recommit Agreed to": "pass",
        "Motion to Proceed Agreed to": "pass",
        "Motion to Proceed Rejected": "fail",
        "Motion Rejected": "fail",
        "Motion to Refer Rejected": "fail",
        "Bill Defeated": "fail",
        "Joint Resolution Passed": "pass",
        "Joint Resolution Defeated": "fail",
        "Point of Order Well Taken": "pass",
        "Resolution Agreed to": "pass",
        "Resolution of Ratification Agreed to": "pass",
        "Veto Sustained": "fail",
    }

    classifications = {
        "HRES": "resolution",
        "HCONRES": "resolution",
        "HR": "bill",
        "HJRES": "resolution",
        "SRES": "resolution",
        "SJRES": "resolution",
        "S": "bill",
        "SCONRES": "resolution",
    }

    # to scrape everything UPDATED after a given date/time, start="2020-01-01 22:01:01"
    def scrape(self, chamber=None, session=None, start=None):
        if start:
            start = datetime.datetime.strptime(start, "%Y-%m-%d %H:%I:%S")
        else:
            start = datetime.datetime(1980, 1, 1, 0, 0, 1)

        sitemap_url = (
            "https://www.govinfo.gov/sitemap/bulkdata/BILLSTATUS/sitemapindex.xml"
        )
        sitemaps = self.get(sitemap_url).content
        root = ET.fromstring(sitemaps)

        # if you want to test a bill:
        # yield from self.parse_bill('https://www.govinfo.gov/bulkdata/BILLSTATUS/118/s/BILLSTATUS-118s4869.xml')

        for link in root.findall("us:sitemap/us:loc", self.ns):
            # split by /, then check that "116s" matches the chamber
            if chamber:
                link_parts = link.text.split("/")
                chamber_code = link_parts[-2][3]
                if chamber_code != self.chamber_map[chamber]:
                    continue

            if session in link.text:
                yield from self.parse_bill_list(link.text, start)

    def parse_bill_list(self, url, start):
        sitemap = self.get(url).content
        root = ET.fromstring(sitemap)
        for row in root.findall("us:url", self.ns):
            date = datetime.datetime.fromisoformat(
                self.get_xpath(row, "us:lastmod")[:-1]
            )

            if date > start:
                bill_url = self.get_xpath(row, "us:loc")
                self.debug(
                    f"{datetime.datetime.strftime(date, '%c')} > {datetime.datetime.strftime(start, '%c')}, scraping {bill_url}"
                )
                yield from self.parse_bill(bill_url)

    def parse_bill(self, url):
        xml = self.get(url).content
        xml = ET.fromstring(xml)

        bill_num = self.get_xpath(xml, "bill/billNumber")
        if not bill_num:
            bill_num = self.get_xpath(xml, "bill/number")

        bill_type = self.get_xpath(xml, "bill/billType")
        if not bill_type:
            bill_type = self.get_xpath(xml, "bill/type")

        bill_id = f"{bill_type} {bill_num}"

        chamber_name = self.get_xpath(xml, "bill/originChamber")
        chamber = self.chambers[chamber_name]

        title = self.get_xpath(xml, "bill/title")

        classification = self.classifications[bill_type]

        session = self.get_xpath(xml, "bill/congress")

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=title,
            classification=classification,
        )

        self.scrape_actions(bill, xml)
        self.scrape_amendments(bill, xml, session, chamber, bill_id)
        self.scrape_cbo(bill, xml)
        self.scrape_committee_reports(bill, xml)
        self.scrape_cosponsors(bill, xml)
        self.scrape_laws(bill, xml)
        self.scrape_related_bills(bill, xml)
        self.scrape_sponsors(bill, xml)
        self.scrape_subjects(bill, xml)
        self.scrape_summaries(bill, xml)
        self.scrape_titles(bill, xml)
        self.scrape_versions(bill, xml)

        for vote in self.scrape_votes(bill, xml):
            yield vote

        xml_url = f"https://www.govinfo.gov/bulkdata/BILLSTATUS/{session}/{bill_type.lower()}/BILLSTATUS-{session}{bill_type.lower()}{bill_num}.xml"
        bill.add_source(xml_url)
        # need to get Congress.gov URL for source & additional versions
        # https://www.congress.gov/bill/116th-congress/house-bill/1
        if "J" in bill_type:
            cg_url = f"https://congress.gov/bill/{session}th-congress/{chamber_name.lower()}-joint-{classification.lower()}/{bill_num}"
        else:
            cg_url = f"https://congress.gov/bill/{session}th-congress/{chamber_name.lower()}-{classification.lower()}/{bill_num}"
        bill.add_source(cg_url)

        # use cg_url to get additional version for public law
        # disabled 9/2021 - congress.gov was giving 503s
        # self.scrape_public_law_version(bill, cg_url)
        for event in self.scrape_hearing_by(bill, xml, xml_url):
            yield event

        yield bill

    def build_sponsor_name(self, row):
        first_name = self.get_xpath(row, "firstName")
        middle_name = self.get_xpath(row, "middleName")
        last_name = self.get_xpath(row, "lastName")
        return " ".join(filter(None, [first_name, middle_name, last_name]))

    # LOC actions don't make the chamber clear, but you can deduce it from the codes
    # https://github.com/usgpo/bill-status/blob/main/BILLSTATUS-XML_User_User-Guide.md
    def classify_actor_by_code(self, action_code: str):
        if action_code is None:
            return False
        # There is a new action code(Intro-H) that is not documented above.
        # Also adding (Intro-S) to mitigate against any surprise in Senate
        if action_code[0:1] == "H" or action_code == "Intro-H":
            return "lower"
        elif action_code[0:1] == "E":
            return "executive"
        elif action_code[0:1] == "S" or action_code == "Intro-S":
            return "upper"

        if action_code.isdigit():
            code = int(action_code)
            if code < 10000:
                return "lower"
            elif code < 28000:
                return "upper"
            else:
                return "executive"

        return False

    def classify_action_by_code(self, action):
        if action is None:
            return None
        # https://github.com/usgpo/bill-status/blob/master/BILLSTATUS-XML_User_User-Guide.md
        # see table 3, Action Code Element Possible Values

        # https://github.com/openstates/openstates-core/blob/082210489693b31e6534bd8328bfb895427e9eed/openstates/data/common.py
        # for the OS codes
        codes = {
            # note: E3000 can also mean vetoed, so catch executive signatures by the action text
            # see https://www.govinfo.gov/bulkdata/BILLSTATUS/116/sjres/BILLSTATUS-116sjres68.xml
            # 'E30000': 'executive-signature',
            "31000": "executive-veto",
            "E20000": "executive-receipt",
            "E40000": "became-law",
            "H11100": "referral-committee",
            "H11200": "referral-committee",
            "H14000": "receipt",
            "1000": "introduction",
            "2000": "referral-committee",
            "8000": "passage",
            "10000": "introduction",
            "11000": "referral-committee",
            "14000": "referral",
            "17000": "passage",
            "28000": "executive-receipt",
            "36000": "became-law",
            # TODO: is this always passage or do we have to check the result?
            # https://www.govinfo.gov/bulkdata/BILLSTATUS/116/hr/BILLSTATUS-116hr8337.xml
            "H37300": "passage",
            "Intro-H": "introduction",
            # new one for senate
            # https://www.govinfo.gov/bulkdata/BILLSTATUS/118/s/BILLSTATUS-118s4869.xml
            "Intro-S": "introduction",
        }

        return codes.get(action)

    def classify_action_by_name(self, action):
        action_classifiers = [
            ("Read the second time", ["reading-2"]),
            ("referred to", ["referral-committee"]),
            (
                "Received in the Senate. Read the first time",
                ["introduction", "reading-1"],
            ),
            ("Signed by President", ["executive-signature"]),
            ("Vetoed by President", ["executive-veto"]),
            ("Failed of passage in Senate over veto by", ["veto-override-failure"]),
        ]
        for regex, classification in action_classifiers:
            if re.match(regex, action):
                return classification
        return None

    def get_xpath(self, xml, xpath):
        if not xml.findall(xpath, self.ns):
            return
        return xml.findall(xpath, self.ns)[0].text

    def scrape_actions(self, bill, xml):
        # TODO: Skip all LOC actions? just some LOC actions?

        # list for deduping
        actions = []
        for row in xml.findall("bill/actions/item"):
            action_text = self.get_xpath(row, "text")
            if action_text not in actions:
                source = self.get_xpath(row, "sourceSystem/name")

                if source is None:
                    self.warning(f"Skipping action with no source: {action_text}")
                    continue

                action_type = self.get_xpath(row, "type")
                actor = "lower"
                if "Senate" in source:
                    actor = "upper"
                elif "House" in source:
                    actor = "lower"
                elif action_type == "BecameLaw" or action_type == "President":
                    actor = "executive"
                elif action_type == "Committee":
                    continue

                # house actions give a time, senate just a date
                if row.findall("actionTime"):
                    action_date = f"{self.get_xpath(row, 'actionDate')} {self.get_xpath(row, 'actionTime')}"
                    action_date = datetime.datetime.strptime(
                        action_date, "%Y-%m-%d %H:%M:%S"
                    )
                else:
                    action_date = datetime.datetime.strptime(
                        self.get_xpath(row, "actionDate"), "%Y-%m-%d"
                    )
                action_date = self._TZ.localize(action_date)

                classification = self.classify_action_by_code(
                    self.get_xpath(row, "actionCode")
                )

                # senate actions dont have a code
                if classification is None:
                    classification = self.classify_action_by_name(action_text)

                # LOC doesn't make the actor clear, but you can back into it
                # from the actions
                if source == "Library of Congress":
                    possible_actor = self.classify_actor_by_code(
                        self.get_xpath(row, "actionCode")
                    )
                    if possible_actor is not None:
                        actor = possible_actor

                if not action_text:
                    action_text = "No action text provided by the source"

                bill.add_action(
                    action_text,
                    action_date,
                    chamber=actor,
                    classification=classification,
                )
                actions.append(action_text)

    # Hearing By
    def scrape_hearing_by(self, bill, xml, url):
        actions = []

        for row in xml.findall("bill/actions/item"):
            action_text = (
                self.get_xpath(row, "text") if self.get_xpath(row, "text") else ""
            )
            if "hearings held" not in action_text.lower():
                continue
            committee_name = self.get_xpath(row, "committees/item/name")
            if action_text in actions:
                continue
            # house actions give a time, senate just a date
            if row.findall("actionTime"):
                action_date = f"{self.get_xpath(row, 'actionDate')} {self.get_xpath(row, 'actionTime')}"
                action_date = datetime.datetime.strptime(
                    action_date, "%Y-%m-%d %H:%M:%S"
                )
            else:
                action_date = datetime.datetime.strptime(
                    self.get_xpath(row, "actionDate"), "%Y-%m-%d"
                )
            action_date = self._TZ.localize(action_date)
            location = "Washington, DC 20004"
            if committee_name:
                event_name = f"{action_text} - {bill.identifier} - {committee_name}"
            else:
                event_name = f"{action_text} - {bill.identifier}"
            event = Event(
                event_name,
                action_date,
                location_name=location,
            )
            if committee_name:
                event.add_committee(committee_name)
            event.add_bill(bill=bill.identifier)

            actions.append(action_text)
            event.add_source(url)

            yield event

    def scrape_amendments(self, bill, xml, session, chamber, bill_id):
        slugs = {
            "HAMDT": "house-amendment",
            "SAMDT": "senate-amendment",
        }

        for row in xml.findall("bill/amendments/amendment"):
            session = self.get_xpath(row, "congress")
            num = self.get_xpath(row, "number")

            # 201st not 200th. If congress.gov's url scheme survivess 10 years,
            # I apologize, future maintainer.
            if int(session) > 200:
                self.warning("Check amendment url ordinals")

            bill.add_document_link(
                note=f"{self.get_xpath(row, 'type')} {num}",
                url=f"https://www.congress.gov/amendment/{session}th-congress/{slugs[self.get_xpath(row, 'type')]}/{num}",
                media_type="text/html",
            )

        # ex: https://rules.house.gov/bill/116/hr-3884
        if chamber == "lower":
            rules_url = (
                f"https://rules.house.gov/bill/{session}/{bill_id.replace(' ', '-')}"
            )
            # FYI: this request may be inefficient, because many bills do not have a page at the generated URL
            # so we may be making a lot of requests that just go to 404
            # additionally, the server occasionally returns 403, and that triggers a backoff/retry which wastes minutes
            # accordingly, we use requests directly and avoid retries
            try:
                page = lxml.html.fromstring(requests.get(rules_url).content)
                page.make_links_absolute(rules_url)
                for row in page.xpath(
                    '//article[contains(@class, "field-name-field-amendment-table")]/div/div/table/tr'
                ):
                    if row.xpath("td[3]/a"):
                        amdt_num = row.xpath("td[1]/text()")[0].strip()
                        amdt_sponsor = row.xpath("td[3]/a/text()")[0].strip()
                        amdt_name = f"House Rules Committee Amendment {amdt_num} - {amdt_sponsor}"
                        self.info(amdt_name)
                        amdt_url = row.xpath("td[3]/a/@href")[0].strip()
                        if not amdt_url.startswith("http"):
                            continue
                        bill.add_document_link(
                            note=amdt_name,
                            url=amdt_url,
                            media_type="application/pdf",
                        )
            except (requests.exceptions.HTTPError, lxml.etree.XMLSyntaxError):
                # Not every bill has a rules committee page
                return

    # CBO cost estimates
    def scrape_cbo(self, bill, xml):
        for row in xml.findall("bill/cboCostEstimates/item"):
            bill.add_document_link(
                note=f"CBO: {self.get_xpath(row, 'title')}",
                url=self.get_xpath(row, "url"),
                media_type="text/html",
            )

    # ex: https://www.govinfo.gov/bulkdata/BILLSTATUS/116/hr/BILLSTATUS-116hr1218.xml
    def scrape_committee_reports(self, bill, xml):
        regex = r"(?P<chamber>[H|S|J])\.\s+Rept\.\s+(?P<session>\d+)-(?P<num>\d+)"

        for row in xml.findall("bill/committeeReports/committeeReport"):
            report = self.get_xpath(row, "citation")
            match = re.search(regex, report)

            url = f"https://www.congress.gov/{match.group('session')}/crpt/{match.group('chamber').lower()}rpt{match.group('num')}/CRPT-{match.group('session')}{match.group('chamber').lower()}rpt{match.group('num')}.pdf"

            bill.add_document_link(note=report, url=url, media_type="application/pdf")

    def scrape_cosponsors(self, bill, xml):
        all_sponsors = []
        for row in xml.findall("bill/cosponsors/item"):
            if not self.get_xpath(row, "sponsorshipWithdrawnDate"):
                bill.add_sponsorship(
                    self.build_sponsor_name(row),
                    classification="cosponsor",
                    primary=False,
                    entity_type="person",
                )
                all_sponsors.append(self.get_xpath(row, "bioguideId"))
        bill.extras["cosponsor_bioguides"] = all_sponsors

    def scrape_laws(self, bill, xml):
        # ex. public law, https://www.govinfo.gov/bulkdata/BILLSTATUS/117/s/BILLSTATUS-117s325.xml
        # ex. private law, https://www.govinfo.gov/bulkdata/BILLSTATUS/115/hr/BILLSTATUS-115hr4641.xml

        for row in xml.findall("bill/laws/item"):
            law_type = self.get_xpath(row, "type")
            law_ref = self.get_xpath(row, "number")

            url_slug = "pvtl" if law_type == "Private Law" else "publ"

            congress, plaw = law_ref.split("-")
            law_url = f"https://www.congress.gov/{congress}/plaws/{url_slug}{plaw}/PLAW-{congress}{url_slug}{plaw}.pdf"

            bill.add_citation(
                f"US {law_type}", law_ref, citation_type="final", url=law_url
            )

    def scrape_related_bills(self, bill, xml):
        for row in xml.findall("bill/relatedBills/item"):
            identifier = (
                f"{self.get_xpath(row, 'type')} {self.get_xpath(row, 'number')}"
            )

            bill.add_related_bill(
                identifier=identifier,
                legislative_session=self.get_xpath(row, "congress"),
                relation_type="companion",
            )

    def scrape_sponsors(self, bill, xml):
        all_sponsors = []
        for row in xml.findall("bill/sponsors/item"):
            if not row.findall("sponsorshipWithdrawnDate"):
                bill.add_sponsorship(
                    self.build_sponsor_name(row),
                    classification="primary",
                    primary=True,
                    entity_type="person",
                )
                all_sponsors.append(self.get_xpath(row, "bioguideId"))
        bill.extras["sponsor_bioguides"] = all_sponsors

    def scrape_subjects(self, bill, xml):
        for row in xml.findall("bill/subjects/billSubjects/legislativeSubjects/item"):
            bill.add_subject(self.get_xpath(row, "name"))

    def scrape_summaries(self, bill, xml):
        seen_abstracts = set()
        for row in xml.findall("bill/summaries/billSummaries/item"):
            abstract = self.get_xpath(row, "text")

            if abstract not in seen_abstracts:
                bill.add_abstract(
                    abstract=abstract,
                    note=self.get_xpath(row, "name"),
                )
                seen_abstracts.add(abstract)

    def scrape_titles(self, bill, xml):
        all_titles = set()
        # add current title to prevent dupes
        all_titles.add(bill.title)

        for alt_title in xml.findall("bill/titles/item"):
            all_titles.add(self.get_xpath(alt_title, "title"))

        all_titles.remove(bill.title)

        for title in all_titles:
            bill.add_title(title)

    def scrape_versions(self, bill, xml):
        for row in xml.findall("bill/textVersions/item"):
            version_title = self.get_xpath(row, "type")
            try:
                version_date = self.get_xpath(row, "date")[:10]
            except TypeError:
                version_date = ""

            for version in row.findall("formats/item"):
                url = self.get_xpath(version, "url")
                bill.add_version_link(
                    note=version_title,
                    url=url,
                    media_type="text/xml",
                    date=version_date,
                )
                bill.add_version_link(
                    note=version_title,
                    url=url.replace("xml", "pdf"),
                    media_type="application/pdf",
                    date=version_date,
                )

    def scrape_public_law_version(self, bill, url):
        # only try to scrape public law version if there's an enrolled version
        if not any(["Enrolled" in v["note"] for v in bill.versions]):
            return
        # S 164 is timing out so skipping for now
        # https://github.com/openstates/issues/issues/482
        elif bill.title == "Advancing Education on Biosimilars Act of 2021":
            return

        resp = self.get(url + "/text")
        doc = lxml.html.fromstring(resp.content)
        doc.make_links_absolute(url)

        try:
            latest_version = doc.xpath("//select[@id='textVersion']/option/text()")[0]
        except IndexError:
            return
        if "Public Law" in latest_version:
            month, day, year = re.findall(r"(\d{2})/(\d{2})/(\d{4})", latest_version)[0]
            date = f"{year}-{month}-{day}"
            latest_version_url = doc.xpath("//a[text()='PDF']/@href")[0]
            bill.add_version_link(
                note="Public Law",
                url=latest_version_url,
                media_type="application/pdf",
                date=date,
            )

    def scrape_votes(self, bill, xml):
        vote_urls = []
        for row in xml.findall("bill/actions/item/recordedVotes/recordedVote"):
            url = self.get_xpath(row, "url")
            chamber = self.get_xpath(row, "chamber")
            if url not in vote_urls:
                vote_urls.append((url, chamber))

        for url, chamber in vote_urls:
            # USA roll call requests sometimes fail for a long time, and the wait on retries
            # piles up very quickly, causing the whole scrape to be over 24 hours
            # so, we use requests library directly to avoid long retries cycle
            try:
                content = requests.get(url).content
                vote_xml = lxml.html.fromstring(content)
                if chamber.lower() == "senate":
                    vote = self.scrape_senate_votes(vote_xml, url)
                elif chamber.lower() == "house":
                    vote = self.scrape_house_votes(bill, vote_xml, url)
                yield vote
            except (requests.exceptions.HTTPError, lxml.etree.XMLSyntaxError):
                self.info(f"Error fetching {url}, skipping (used requests, no retries)")
                return

    def scrape_senate_votes(self, page, url):
        if not page.xpath("//roll_call_vote/vote_date/text()"):
            self.error(f"Unable to parse vote date in {url}")
            return

        vote_date = page.xpath("//roll_call_vote/vote_date/text()")[0].strip()

        when = self._TZ.localize(
            datetime.datetime.strptime(vote_date, "%B %d, %Y, %H:%M %p")
        )

        session = page.xpath("//roll_call_vote/congress/text()")[0]

        roll_call = page.xpath("//roll_call_vote/vote_number/text()")[0]
        vote_id = "us-{}-upper-{}".format(when.year, roll_call)

        # note: not everything the senate votes on is a bill, this is OK
        # non bills include nominations and impeachments
        doc_type = page.xpath("//roll_call_vote/document/document_type/text()")[0]

        if page.xpath("//roll_call_vote/amendment/amendment_to_document_number/text()"):
            bill_id = page.xpath(
                "//roll_call_vote/amendment/amendment_to_document_number/text()"
            )[0].replace(".", "")
        else:
            bill_id = page.xpath("//roll_call_vote/document/document_name/text()")[
                0
            ].replace(".", "")

        if re.match(r"PN\d*", bill_id):
            return

        motion = page.xpath("//roll_call_vote/vote_question_text/text()")[0]

        result_text = page.xpath("//roll_call_vote/vote_result/text()")[0]

        result = self.senate_statuses[result_text]

        vote = VoteEvent(
            start_date=when,
            bill_chamber="lower" if doc_type[0] == "H" else "upper",
            motion_text=motion,
            classification="passage",  # TODO
            result=result,
            legislative_session=session,
            identifier=vote_id,
            bill=bill_id,
            chamber="upper",
        )

        vote.add_source(url)

        vote.extras["senate-rollcall-num"] = roll_call

        yeas = page.xpath("//roll_call_vote/count/yeas/text()")[0]
        nays = page.xpath("//roll_call_vote/count/nays/text()")[0]

        if page.xpath("//roll_call_vote/count/absent/text()"):
            absents = page.xpath("//roll_call_vote/count/absent/text()")[0]
        else:
            absents = 0

        if page.xpath("//roll_call_vote/count/present/text()"):
            presents = page.xpath("//roll_call_vote/count/present/text()")[0]
        else:
            presents = 0

        vote.set_count("yes", int(yeas))
        vote.set_count("no", int(nays))
        vote.set_count("absent", int(absents))
        vote.set_count("abstain", int(presents))

        for row in page.xpath("//roll_call_vote/members/member"):
            lis_id = row.xpath("lis_member_id/text()")[0]
            name = row.xpath("member_full/text()")[0]
            choice = row.xpath("vote_cast/text()")[0]

            vote.vote(self.vote_codes[choice], name, note=lis_id)

        yield vote

    def scrape_house_votes(self, bill, page, url):
        vote_date = page.xpath("//rollcall-vote/vote-metadata/action-date/text()")[0]
        vote_time = page.xpath("//rollcall-vote/vote-metadata/action-time/@time-etz")[0]

        when = self._TZ.localize(
            datetime.datetime.strptime(
                "{} {}".format(vote_date, vote_time), "%d-%b-%Y %H:%M"
            )
        )

        motion = page.xpath("//rollcall-vote/vote-metadata/vote-question/text()")[0]
        result = page.xpath("//rollcall-vote/vote-metadata/vote-result/text()")[0]
        if result == "Passed":
            result = "pass"
        else:
            result = "fail"

        session = page.xpath("//rollcall-vote/vote-metadata/congress/text()")[0]

        if not page.xpath("//rollcall-vote/vote-metadata/legis-num/text()"):
            self.warning(f"No bill id for {url}, skipping")
            return

        bill_id = page.xpath("//rollcall-vote/vote-metadata/legis-num/text()")[0]
        # for some reason these are "H R 123" which nobody uses, so fix to "HR 123"
        bill_id = re.sub(r"([A-Z])\s([A-Z])", r"\1\2", bill_id)

        roll_call = page.xpath("//rollcall-vote/vote-metadata/rollcall-num/text()")[0]

        vote_id = "us-{}-lower-{}".format(when.year, roll_call)

        vote = VoteEvent(
            start_date=when,
            bill_chamber="lower" if bill_id[0] == "H" else "upper",
            motion_text=motion,
            classification="passage",  # TODO
            result=result,
            legislative_session=session,
            identifier=vote_id,
            bill=bill_id,
            chamber="lower",
        )
        vote.add_source(url)

        vote.extras["house-rollcall-num"] = roll_call

        yeas = page.xpath(
            "//rollcall-vote/vote-metadata/vote-totals/totals-by-vote/yea-total/text()"
        )[0]
        nays = page.xpath(
            "//rollcall-vote/vote-metadata/vote-totals/totals-by-vote/nay-total/text()"
        )[0]
        nvs = page.xpath(
            "//rollcall-vote/vote-metadata/vote-totals/totals-by-vote/not-voting-total/text()"
        )[0]
        presents = page.xpath(
            "//rollcall-vote/vote-metadata/vote-totals/totals-by-vote/present-total/text()"
        )[0]

        vote.set_count("yes", int(yeas))
        vote.set_count("no", int(nays))
        vote.set_count("not voting", int(nvs))
        vote.set_count("abstain", int(presents))

        # vote.yes vote.no vote.vote
        for row in page.xpath("//rollcall-vote/vote-data/recorded-vote"):
            bioguide = row.xpath("legislator/@name-id")[0]
            name = row.xpath("legislator/@sort-field")[0]
            choice = row.xpath("vote/text()")[0]

            vote.vote(self.vote_codes[choice], name, note=bioguide)

        return vote
